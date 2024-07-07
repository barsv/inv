def get_trailing_stop_loss_long_profits(df, trailing_stop_loss_percent = 0.15 * 0.01):
    opens = df['open'].to_numpy()
    highs = df['high'].to_numpy()
    lows = df['low'].to_numpy()
    n = len(opens)
    profits = []
    stop_loss_prices = []
    maximums = []
    x0 = 0
    while x0 < n:
        max_high_x = x0
        max_high = highs[x0]
        sl_size = max_high * trailing_stop_loss_percent
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
                sl_size = max_high * trailing_stop_loss_percent
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
