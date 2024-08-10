import datetime
import df2npz
import history_data_loader
img_creator = __import__('1T')


symbol = 'BTCUSDT'
time_from = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=3, minutes=0) # 2-33, 150 минутных свечек + 3 минуты запаса

df = history_data_loader.load_1T_klines(symbol, time_from)
df_bars = df2npz.convert_to_1T_bars(df)
charts_at = df_bars.index[-1]

img_creator.create_1T_image(df_bars, charts_at)