# pip install numpy
# pip install pandas

import os
import pandas as pd
import numpy as np

def convert_to_5s_bars(filename, output_filename):
    # Загрузка данных из CSV
    df = pd.read_csv(filename)

    # Конвертация timestamp из UNIX в datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')

    # Установка timestamp как индекса DataFrame
    df.set_index('timestamp', inplace=True)

    # Группировка данных по 5-секундным интервалам
    resampled_df = df.resample('5S').agg({
        'price': ['first', 'max', 'min', 'last'],
        'size': 'sum'
    })

    # Переименование столбцов
    resampled_df.columns = ['open', 'high', 'low', 'close', 'vol']

    # Заполнение пропущенных значений для 'open', 'high', 'low', 'close' методом ffill
    resampled_df[['open', 'high', 'low', 'close']] = resampled_df[['open', 'high', 'low', 'close']].ffill()

    # Замена возможных NaN в 'vol' на 0
    resampled_df['vol'].fillna(0, inplace=True)
    
    # Сброс индекса для преобразования временного индекса обратно в столбец
    resampled_df.reset_index(inplace=True)

    # Сохранение в файл .npz
    np.savez(output_filename, data=resampled_df.values)
    print(f"Файл '{output_filename}' успешно сохранён.")

def convert_all_csv_in_directory(input_dir, output_dir):
    # Создание выходной директории, если она не существует
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Создана директория: {output_dir}")

    # Перечисление всех файлов в директории
    for filename in sorted(os.listdir(input_dir)):
        if filename.endswith('.csv'):
            input_filepath = os.path.join(input_dir, filename)
            output_filename = os.path.join(output_dir, os.path.splitext(filename)[0] + '.npz')
            
            # Проверка, существует ли уже файл npz
            if os.path.exists(output_filename):
                print(f"Файл '{output_filename}' уже существует. Обработка пропущена.")
                continue
            
            # Конвертация файла
            convert_to_5s_bars(input_filepath, output_filename)

# Пример использования:
# convert_all_csv_in_directory('/path/to/your/input/directory', '/path/to/your/output/directory')
convert_all_csv_in_directory('csv/BTCUSD', 'npz/BTCUSD')
