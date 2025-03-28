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
        ('fast_period', 20),
        ('slow_period', 50),
        ('trend_period', 200),
        ('rsi_period', 14),
        ('rsi_overbought', 60),
        ('rsi_oversold', 40),
        ('crossover_threshold', 0.00005),
        ('trailing_stop', 0.01),  # 1% trailing stop
    )

    def __init__(self):
        self.fast_hma = HullMovingAverage(self.data.close, period=self.params.fast_period)
        self.slow_hma = HullMovingAverage(self.data.close, period=self.params.slow_period)
        self.trend_hma = HullMovingAverage(self.data.close, period=self.params.trend_period)
        self.crossover = bt.indicators.CrossOver(self.fast_hma, self.slow_hma)
        self.rsi = bt.indicators.RSI(self.data.close, period=self.params.rsi_period)
        self.entry_price = None
        self.highest_price = None  # Track the highest price for trailing stop

    def log(self, txt):
        dt = self.datas[0].datetime.datetime(0)
        print(f'{dt}: {txt}')

    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED at {order.executed.price}')
            elif order.issell():
                self.log(f'SELL EXECUTED at {order.executed.price}')
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f'Order {order.status}')

    def next(self):
        hma_diff = (self.fast_hma[0] - self.slow_hma[0]) / self.slow_hma[0]
        trend_up = self.data.close[0] > self.trend_hma[0]

        # Check trailing stop-loss
        if self.position:
            current_price = self.data.close[0]
            if self.entry_price:
                # Update the highest price seen since entry
                if current_price > self.highest_price:
                    self.highest_price = current_price
                # Calculate the trailing stop price (1% below the highest price)
                trailing_stop_price = self.highest_price * (1 - self.params.trailing_stop)
                # If the current price falls below the trailing stop, close the position
                if current_price <= trailing_stop_price:
                    self.log(f'Trailing Stop triggered at {current_price} (Highest: {self.highest_price})')
                    self.close()
                    self.entry_price = None
                    self.highest_price = None

        # Buy signal
        if (self.crossover > 0 and 
            hma_diff > self.params.crossover_threshold and 
            self.rsi < self.params.rsi_overbought and 
            trend_up):
            if not self.position:
                self.entry_price = self.data.close[0]
                self.highest_price = self.entry_price  # Initialize highest price
                self.buy()
                self.log(f'BUY at {self.entry_price}')

        # Sell signal
        elif (self.crossover < 0 and 
              hma_diff < -self.params.crossover_threshold and 
              self.rsi > self.params.rsi_oversold and 
              not trend_up):
            if self.position:
                self.sell()
                self.log(f'SELL at {self.data.close[0]}')
                self.entry_price = None
                self.highest_price = None

# Set up the backtest
cerebro = bt.Cerebro()
cerebro.addstrategy(HMACrossoverStrategy)

# Add the data to cerebro
data = bt.feeds.PandasData(dataname=df)
cerebro.adddata(data)

# Set initial cash
cerebro.broker.setcash(100000.0)  # Starting capital: $100,000

# Set IBKR commission: $0.0035 per share, minimum $0.35 per trade
class IBKRCommission(bt.CommInfoBase):
    params = (
        ('commission', 0.0035),  # $0.0035 per share
        ('min_commission', 0.35),  # Minimum $0.35 per trade
        ('stocklike', True),
        ('commtype', bt.CommInfoBase.COMM_FIXED),
    )

    def _getcommission(self, size, price, pseudoexec):
        comm = abs(size) * self.p.commission
        return max(comm, self.p.min_commission)

# Apply the custom commission scheme
#cerebro.broker.setcommission(commission=0.0035, commtype=bt.CommInfoBase.COMM_FIXED, stocklike=True)
#cerebro.addcommissioninfo(IBKRCommission())
cerebro.broker.addcommissioninfo(IBKRCommission())

# Set position sizing: 100 shares per trade
cerebro.addsizer(bt.sizers.FixedSize, stake=100)

# Enable margin checks
cerebro.broker.set_checksubmit(True)

# Add analyzers
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