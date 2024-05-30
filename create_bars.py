import os
import numpy as np
import pandas as pd


def load_npz(directory):
    # Подготовка пустого DataFrame
    data_frames = []

    # Загрузка всех .npz файлов в директории
    for file in sorted(os.listdir(directory)):
        if file.endswith('.npz'):
            data = np.load(os.path.join(directory, file), allow_pickle=True)['data']
            temp_df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'vol'])
            temp_df['timestamp'] = pd.to_datetime(temp_df['timestamp'], unit='s')
            temp_df.set_index('timestamp', inplace=True)
            data_frames.append(temp_df)
            print(f'loaded {file}')

    print('concatinating...')
    # Объединение всех DataFrame в один
    full_data = pd.concat(data_frames) 

    print('sorting...')
    # Сортировка данных по времени
    full_data.sort_index(inplace=True)

    return full_data


def resample_npz(full_data, period):
    print('resampling...')
    # Ресемплирование данных в интервалы
    resampled_data = full_data.resample(period).agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'vol': 'sum'
    })

    # Замена возможных NaN значений на 0 или предыдущее значение
    resampled_data['vol'].fillna(0, inplace=True)
    resampled_data[['open', 'high', 'low', 'close']] = resampled_data[['open', 'high', 'low', 'close']].ffill()

    # Сброс индекса для преобразования временного индекса обратно в столбец
    resampled_data.reset_index(inplace=True)

    return resampled_data


def save_resampled_data_to_npz(resampled_data, output_directory, output_filename='5min_bars.npz'):
    # Создание выходной директории, если не существует
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
    
    # Сохранение обработанных данных
    output_path = os.path.join(output_directory, output_filename)
    print('saving...')
    np.savez(output_path, data=resampled_data.values)
    print(f"bars saved to '{output_path}'.")


def create_bars(symbol):
    directory = f'npz/{symbol}'
    output_directory = 'npz'
    full_data = load_npz(directory)
    # 1 minute bars
    period = '1T'
    resampled_data = resample_npz(full_data, period)
    save_resampled_data_to_npz(resampled_data, output_directory, f'{symbol}_{period}.npz')
    # 5 minute bars
    period = '5T'
    resampled_data = resample_npz(full_data, period)
    save_resampled_data_to_npz(resampled_data, output_directory, f'{symbol}_{period}.npz')
    # 1 hour bars
    period = '1H'
    resampled_data = resample_npz(full_data, period)
    save_resampled_data_to_npz(resampled_data, output_directory, f'{symbol}_{period}.npz')
    # 1 day bars
    period = 'D'
    resampled_data = resample_npz(full_data, period)
    save_resampled_data_to_npz(resampled_data, output_directory, f'{symbol}_{period}.npz')


# Использование функций
create_bars('BTCUSD')