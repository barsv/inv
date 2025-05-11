# SSA reversal strategy implemented in Backtrader (v0.3)
# =========================================================
# Author: ChatGPT – updated 10 May 2025
#
# Changelog v0.3
#  • Убрана зависимость от argparse: параметры теперь задаются прямо в блоке
#    `if __name__ == "__main__":` для быстрого запуска из IDE.
#  • Логика SSA/стратегии не тронута.
#
# ‼️ DISCLAIMER ‼️  (as before)

import backtrader as bt
import pandas as pd
import numpy as np
from numpy.linalg import svd
from typing import Sequence, List, Union

# ---------------------------------------------------------------------------
# Helper to reconstruct a chosen set of SSA components back to a single series
# ---------------------------------------------------------------------------

def reconstruct_trend(U, s, Vt, window: int, idx: Sequence[int]):
    if not idx:
        raise ValueError("`idx` must contain at least one component index to keep")
    Xn = (U[:, idx] * s[idx]) @ Vt[idx, :]
    M, K = Xn.shape
    N = M + K - 1
    recon = np.zeros(N)
    counts = np.zeros(N)
    for i in range(M):
        recon[i : i + K] += Xn[i]
        counts[i : i + K] += 1
    return recon / counts

# ---------------------------------------------------------------------------
# SSAIndicator – calculates the latest trend value and its first difference
# ---------------------------------------------------------------------------

class SSAIndicator(bt.Indicator):
    lines = ("trend", "slope")
    params = dict(window=60, k_trend=list(range(5)))

    def __init__(self):
        raw = self.p.k_trend
        if isinstance(raw, int):
            if raw <= 0:
                raise ValueError("k_trend integer must be >= 1")
            self.ktrend: List[int] = list(range(raw))
        else:
            self.ktrend = list(raw) or [0]
        self.addminperiod(self.p.window + 1)

    def _compute_trend(self, series: np.ndarray):
        window = self.p.window
        # Use only the last 5*window points for computational efficiency (N = max(5*window, window+1))
        min_len = 5 * window
        if len(series) > min_len:
            series = series[-min_len:]
        X = np.vstack([series[i : i + len(series) - window + 1] for i in range(window)])
        U, s, Vt = svd(X, full_matrices=False)
        effective = [i for i in self.ktrend if i < s.size] or [0]
        return reconstruct_trend(U, s, Vt, window, effective)[-1]

    def next(self):
        series = np.array(self.data.get(size=len(self)))
        if len(series) < self.p.window:
            return
        trend_val = self._compute_trend(series)
        self.lines.trend[0] = trend_val
        self.lines.slope[0] = trend_val - self.lines.trend[-1] if len(self) > self.p.window else 0.0

# ---------------------------------------------------------------------------
# Strategy – flip position when the SSA trend slope changes sign
# ---------------------------------------------------------------------------

class SSASlopeFlipStrategy(bt.Strategy):
    params = dict(window=60, k_trend=list(range(5)), stake=1)

    def __init__(self):
        self.ssa = SSAIndicator(self.data.close, window=self.p.window, k_trend=self.p.k_trend)
        self.order = None

    def log(self, txt):
        dt = self.data.datetime.datetime(0)
        print(f"{dt:%Y-%m-%d %H:%M:%S} : {txt}")

    def next(self):
        if len(self) <= self.p.window + 1:
            return
        slope_now, slope_prev = self.ssa.slope[0], self.ssa.slope[-1]
        if slope_now * slope_prev < 0:
            if self.order:
                self.cancel(self.order)
            desired_long = slope_now > 0
            if desired_long and self.position.size <= 0:
                self.log("Flip to LONG")
                self.order = self.close() if self.position else self.buy(size=self.p.stake)
            elif not desired_long and self.position.size >= 0:
                self.log("Flip to SHORT")
                self.order = self.close() if self.position else self.sell(size=self.p.stake)

    def notify_order(self, order):
        if order.status in (order.Completed, order.Canceled, order.Margin):
            self.order = None

# ---------------------------------------------------------------------------
# run_backtest utility
# ---------------------------------------------------------------------------

def run_backtest(csv_path: str, initial_cash: float = 100_000.0, window: int = 60, k_trend: Union[int, Sequence[int]] = 5):
    if isinstance(k_trend, int):
        if k_trend <= 0:
            raise ValueError("k_trend integer must be >=1")
        k_trend = list(range(k_trend))
    else:
        k_trend = list(k_trend)

    cerebro = bt.Cerebro()
    cerebro.broker.setcash(initial_cash)

    df = pd.read_csv(csv_path, sep="\t")
    df = df[:1000]
    df["Datetime"] = pd.to_datetime(df["<DATE>"] + " " + df["<TIME>"])
    df.set_index("Datetime", inplace=True)
    df.drop(columns=["<DATE>", "<TIME>"], inplace=True)
    df.rename(columns={"<OPEN>": "Open", "<HIGH>": "High", "<LOW>": "Low", "<CLOSE>": "Close", "<VOL>": "Volume"}, inplace=True)
    df = df[["Open", "High", "Low", "Close", "Volume"]]

    data = bt.feeds.PandasData(dataname=df, timeframe=bt.TimeFrame.Minutes, compression=1)
    cerebro.adddata(data)
    cerebro.addstrategy(SSASlopeFlipStrategy, window=window, k_trend=k_trend)

    print(f"Starting Portfolio Value: {cerebro.broker.getvalue():.2f}")
    cerebro.run(maxcpus=1)
    print(f"Final   Portfolio Value: {cerebro.broker.getvalue():.2f}")
    # Show charts after backtest
    cerebro.plot(style='candlestick')

# ---------------------------------------------------------------------------
# Quick‑start entry‑point – edit values below and run script directly
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    run_backtest(
        "./csv/MSFT_M1_202402291729_202503272108.csv",  # path to your dataset
        initial_cash=10_000,  # starting capital
        window=60,            # SSA embedding window
        k_trend=5,            # use components 0..4 as trend
    )
