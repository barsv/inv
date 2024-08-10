import ccxt # type: ignore
import pandas as pd


def load_1T_klines(symbol, time_from):
    exchange = ccxt.bybit()

    iso_formatted_time = time_from.isoformat()
    from_ts = exchange.parse8601(iso_formatted_time)
    
    ohlcv = exchange.fetch_ohlcv(symbol, '1m', from_ts, limit=1000)

    while True:
        from_ts = ohlcv[-1][0]
        new_ohlcv = exchange.fetch_ohlcv(symbol, '1m', from_ts, limit=1000)
        ohlcv.extend(new_ohlcv)
        
        if len(new_ohlcv)!=1000:
            break

    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

    return df