import backtrader as bt
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Load the data

# Load the data (tab-separated file)
df = pd.read_csv('../csv/MSFT_M1_202402291729_202503272108.csv', sep='\t')  # Use tab as the separator
df['Datetime'] = pd.to_datetime(df['<DATE>'] + ' ' + df['<TIME>'])  # Use the correct column names
df.set_index('Datetime', inplace=True)
df.drop(columns=['<DATE>', '<TIME>'], inplace=True)  # Drop the original columns
# Rename columns to match what backtrader expects (optional, if needed)
df.rename(columns={'<OPEN>': 'Open', '<HIGH>': 'High', '<LOW>': 'Low', '<CLOSE>': 'Close', '<TICKVOL>': 'Volume'}, inplace=True)

# Custom Hull Moving Average Indicator
class HullMovingAverage(bt.Indicator):
    lines = ('hma',)
    params = (('period', 9),)  # Default HMA period

    def __init__(self):
        # Step 1: Calculate WMA(n/2) and WMA(n)
        wma_n = bt.indicators.WeightedMovingAverage(self.data, period=self.params.period)
        wma_n2 = bt.indicators.WeightedMovingAverage(self.data, period=int(self.params.period / 2))
        
        # Step 2: 2 * WMA(n/2) - WMA(n)
        raw_hma = 2 * wma_n2 - wma_n
        
        # Step 3: WMA of the result with period sqrt(n)
        self.lines.hma = bt.indicators.WeightedMovingAverage(raw_hma, period=int(np.sqrt(self.params.period)))

# Define the strategy
class HMACrossoverStrategy(bt.Strategy):
    params = (
        ('fast_period', 20),   # Increased Fast HMA period
        ('slow_period', 50),   # Increased Slow HMA period
        ('trend_period', 200), # Long-term trend HMA
        ('rsi_period', 14),    # RSI period
        ('rsi_overbought', 60),  # Tightened RSI overbought level
        ('rsi_oversold', 40),    # Tightened RSI oversold level
        ('crossover_threshold', 0.00005),  # 0.5% threshold for HMA crossover
        ('stop_loss', 0.01),     # 1% stop-loss
        ('take_profit', 0.02),   # 2% take-profit
    )

    def __init__(self):
        # Define the fast, slow, and trend HMAs
        self.fast_hma = HullMovingAverage(self.data.close, period=self.params.fast_period)
        self.slow_hma = HullMovingAverage(self.data.close, period=self.params.slow_period)
        self.trend_hma = HullMovingAverage(self.data.close, period=self.params.trend_period)
        self.crossover = bt.indicators.CrossOver(self.fast_hma, self.slow_hma)
        
        # Add RSI for confirmation
        self.rsi = bt.indicators.RSI(self.data.close, period=self.params.rsi_period)

        # Track entry price for stop-loss/take-profit
        self.entry_price = None

    def next(self):
        # Calculate the percentage difference between fast and slow HMA
        hma_diff = (self.fast_hma[0] - self.slow_hma[0]) / self.slow_hma[0]

        # Determine the trend direction (based on price vs. trend HMA)
        trend_up = self.data.close[0] > self.trend_hma[0]

        # Buy signal: Fast HMA crosses above Slow HMA, significant difference, RSI not overbought, and in an uptrend
        if (self.crossover > 0 and 
            hma_diff > self.params.crossover_threshold and 
            self.rsi < self.params.rsi_overbought and 
            trend_up):
            if not self.position:
                self.entry_price = self.data.close[0]
                self.buy()
                # Set stop-loss and take-profit
                self.sell(exectype=bt.Order.Stop, price=self.entry_price * (1 - self.params.stop_loss))
                self.sell(exectype=bt.Order.Limit, price=self.entry_price * (1 + self.params.take_profit))

        # Sell signal: Fast HMA crosses below Slow HMA, significant difference, RSI not oversold, and in a downtrend
        elif (self.crossover < 0 and 
              hma_diff < -self.params.crossover_threshold and 
              self.rsi > self.params.rsi_oversold and 
              not trend_up):
            if self.position:
                self.entry_price = None
                self.sell()
                

# Set up the backtest
cerebro = bt.Cerebro()
cerebro.addstrategy(HMACrossoverStrategy)

# Add the data to cerebro
data = bt.feeds.PandasData(dataname=df)
cerebro.adddata(data)

# Set initial cash and commission
cerebro.broker.setcash(10000.0)  # Starting capital: $10,000
cerebro.broker.setcommission(commission=0.0005)  # 0.05% commission per trade (more realistic for stocks)

# Set position sizing: Risk $100 per trade
cerebro.addsizer(bt.sizers.FixedSize, stake=1000 // df['Close'].mean())  # $1,000 worth of MSFT per trade

# Add analyzers to track performance
cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')

# Run the backtest
print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())
results = cerebro.run()
print('Ending Portfolio Value: %.2f' % cerebro.broker.getvalue())

# Print performance metrics
sharpe = results[0].analyzers.sharpe.get_analysis()
drawdown = results[0].analyzers.drawdown.get_analysis()
trades = results[0].analyzers.trades.get_analysis()

print(f"Sharpe Ratio: {sharpe['sharperatio']:.2f}")
print(f"Max Drawdown: {drawdown['max']['drawdown']:.2f}%")
print(f"Total Trades: {trades['total']['total']}")
print(f"Winning Trades: {trades['won']['total']}")
print(f"Losing Trades: {trades['lost']['total']}")

# Plot the results
cerebro.plot()
plt.show()