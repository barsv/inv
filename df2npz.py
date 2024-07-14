import os
import pandas as pd
import numpy as np

def convert_to_1T_bars(df):
    # Конвертация timestamp из UNIX в datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

    # Установка timestamp как индекса DataFrame
    df.set_index('timestamp', inplace=True)

    # Группировка данных по 5-секундным интервалам
    resampled_df = df.resample('1T').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    })

    # Переименование столбцов
    resampled_df.columns = ['open', 'high', 'low', 'close', 'volume']

    # Заполнение пропущенных значений для 'open', 'high', 'low', 'close' методом ffill
    resampled_df[['open', 'high', 'low', 'close']] = resampled_df[['open', 'high', 'low', 'close']].ffill()

    # Замена возможных NaN в 'volume' на 0
    resampled_df['volume'].fillna(0, inplace=True)
    
    print(f"Данные успешно загружен!")

    return resampled_df