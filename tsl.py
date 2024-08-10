import pandas_ta as ta
import pandas as pd

def get_trailing_stop_loss_long_profits(df, trailing_stop_loss_percent = 0.15 * 0.01):
    opens = df['open'].to_numpy()
    highs = df['high'].to_numpy()
    lows = df['low'].to_numpy()
    # volatility = (df['high'] - df['low'])
    # volatility_ema2 = ta.sma(df['low'], 60)
    # volatility_ema2.bfill(inplace=True)
    # volatility_ema2 = volatility_ema2.to_numpy()
    # volatility_ema20 = ta.ema(volatility, 20)
    # volatility_ema20.bfill(inplace=True)
    # volatility_ema20 = volatility_ema20.to_numpy()
    # volatility_multiplier = 1 + volatility_ema2 / volatility_ema20
    n = len(opens)
    profits = []
    stop_loss_prices = []
    maximums = []
    x0 = 0
    while x0 < n:
        max_high_x = x0
        max_high = highs[x0]
        sl_size = trailing_stop_loss_percent * max_high # -  volatility_ema2[x0])
        sl_price = max_high - sl_size
        local_stop_loss_prices = [sl_price]
        local_maximums = [max_high]
        # check if we should close the just opened position right on the current bar.
        if opens[x0] - lows[x0] > sl_size:
            # means closing on the first bar.
            profits.append(sl_price - opens[x0])
            maximums.append(max_high)
            stop_loss_prices.append(sl_price)
            x0 += 1
            continue
        # if we reach here then we haven't closed on the first bar. let's check next bars.
        x = x0 + 1
        while x < n and lows[x] > sl_price:
            # if a new max is found then update sl_price so that it will be a *trailing* stop loss.
            if max_high < highs[x]:
                max_high = highs[x]
                max_high_x = x
            sl_size = trailing_stop_loss_percent * max_high # -  volatility_ema2[x])
            sl_price = max_high - sl_size
            local_stop_loss_prices.append(sl_price)
            local_maximums.append(max_high)
            x += 1
        # if we stopped because reached the end of data then we don't know closing price for the currently opened positon.
        if x == n:
            profits.append(None)
            maximums.append(None)
            stop_loss_prices.append(None)
            x0 += 1
            continue
        # if we reach here then current open was closed by sl and not because of the end of data.
        x = x0
        while x <= max_high_x:
            profits.append(sl_price - opens[x])
            stop_loss_prices.append(local_stop_loss_prices[x - x0])
            maximums.append(local_maximums[x - x0])
            x += 1
        x0 = max_high_x + 1
    return (profits, stop_loss_prices, maximums)

def get_trailing_stop_loss_short_profits(df, trailing_stop_loss_percent = 0.15 * 0.01):
    opens = df['open'].to_numpy()
    highs = df['high'].to_numpy()
    lows = df['low'].to_numpy()
    n = len(opens)
    profits = []
    stop_loss_prices = []
    minimums = []
    x0 = 0
    while x0 < n:
        min_low_x = x0
        min_low = lows[x0]
        sl_size = trailing_stop_loss_percent * min_low
        sl_price = min_low + sl_size
        local_stop_loss_prices = [sl_price]
        local_minimums = [min_low]
        # check if we should close the just opened position right on the current bar.
        if highs[x0] - opens[x0] > sl_size:
            # means closing on the first bar.
            profits.append(opens[x0] - sl_price)
            minimums.append(min_low)
            stop_loss_prices.append(sl_price)
            x0 += 1
            continue
        # if we reach here then we haven't closed on the first bar. let's check next bars.
        x = x0 + 1
        while x < n and highs[x] < sl_price:
            # if a new max is found then update sl_price so that it will be a *trailing* stop loss.
            if min_low > lows[x]:
                min_low = lows[x]
                min_low_x = x
            sl_size = trailing_stop_loss_percent * min_low
            sl_price = min_low + sl_size
            local_stop_loss_prices.append(sl_price)
            local_minimums.append(min_low)
            x += 1
        # if we stopped because reached the end of data then we don't know closing price for the currently opened positon.
        if x == n:
            profits.append(None)
            minimums.append(None)
            stop_loss_prices.append(None)
            x0 += 1
            continue
        # if we reach here then current open was closed by sl and not because of the end of data.
        x = x0
        while x <= min_low_x:
            profits.append(opens[x] - sl_price)
            stop_loss_prices.append(local_stop_loss_prices[x - x0])
            minimums.append(local_minimums[x - x0])
            x += 1
        x0 = min_low_x + 1
    return (profits, stop_loss_prices, minimums)
