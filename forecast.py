# этот скрипт делает график минутных свечей с индикаторами и отправляет его в чат жпт на анализ.

#%pip install numpy
#%pip install pandas
#%pip install mplfinance
#%pip install matplotlib
#%pip install ta
#%pip install pandas_ta
#%pip install python-dotenv

import numpy as np
import pandas as pd
import mplfinance as mpf
import matplotlib.pyplot as plt
#import ta # https://github.com/bukosabino/ta
import pandas_ta as ta

import base64
import requests
from dotenv import load_dotenv
import os
import json

import csv
import datetime

# параметры:
points = 150 # количество свечей на графике
chart_period = '1T' # 1 minute

# DPI в matplotlib = 96 пикселов на дюйм. а размер графика задается в дюймах. поэтому делаю пересчет.
dpi = 96
# магические числа 1.232 и 1.352 подобраны методом тыка, чтобы сохраненный png был ровно 1024x768.
# магические числа 1.285 и 1.352 подобраны методом тыка, чтобы сохраненный png был ровно 1536x768.
width_in_inches = (1024 * 1.232) / dpi
height_in_inches = (768 * 1.352) / dpi

# стиль графика для mpl. пытаюсь сделать что-то похожее на светлую тему tradingview.
customstyle = mpf.make_mpf_style(base_mpf_style='yahoo', facecolor='w')
image_path = f'img/{chart_period}.png'

# Загрузка переменных из файла .env
load_dotenv()

# Получение значения переменной OPENAI_API_KEY
api_key = os.getenv('OPENAI_API_KEY')

headers = {
  "Content-Type": "application/json",
  "Authorization": f"Bearer {api_key}"
}

def get_df(symbol, date_time, period):
    """
    Загрузить датафрейм с диска.
    
    Параметры:
    symbol: string
        Например, BTCUSD.
    date_time : string
        Например, 2024-05-29 08:10. Время не обязательно должно попадать в точку графика (будет взята ближайшая точка).
    period : string
        Допустимые значения: '5S' - 5 секунд, '1T' - 1 minute, '5T' - 5 minutes, '1H' - 1 hour, 'D' - 1 day.
    """
    if period == '5S': # пятисекундные свечи
        # '2024-05-29 08:10' -> '2024-05-29'
        date = date_time[:10]
        filename = f'npz/{symbol}/{symbol}{date}.npz'
    else:
        filename = f'npz/{symbol}_{period}.npz'

    # зачитывание в формате numpy
    data = np.load(filename, allow_pickle=True)['data']
    # преобразование в формат pandas
    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

    # Преобразование 'timestamp' в datetime и установка его как индекс DataFrame
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)

    # Преобразование всех столбцов с ценами и объемом в числовой формат
    for column in ['open', 'high', 'low', 'close', 'volume']:
        df[column] = pd.to_numeric(df[column], errors='coerce')
    return df


def get_df_for_chart(symbol, date_time, period, length = 1000):
    """
    Загрузить датафрейм с диска и взять с него слайс.
    
    Параметры:
    date_time : string
        Например, 2024-05-29 08:10. Время не обязательно должно попадать в точку графика (будет взята ближайшая точка).
    period : string
        Допустимые значения: '5S' - 5 секунд, '1T' - 1 minute, '5T' - 5 minutes, '1H' - 1 hour, 'D' - 1 day.
    length : number
        Сколько точек надо в датафрейме.
    """
    df = get_df(symbol, date_time, period)
    # поиск интересной точки.
    date_to_find = date_to_find = pd.Timestamp(date_time)
    index_position = df.index.get_indexer([date_to_find], method='nearest')[0]
    # беру часть точек, чтобы не напрягать либу технического анализа большим количеством точек.
    df = df[index_position-length:index_position]
    return df


def create_image(df):
    print(f'Creating chart image...')
    atr = ta.atr(df[-points-10:]['high'],df[-points-10:]['low'],df[-points-10:]['close'], 10)
    vwap = ta.vwap(df[-points:]['high'],df[-points:]['low'],df[-points:]['close'],df[-points:]['volume'])
    macd = ta.macd(df[-points-200:]['close'], fast=12, slow=26, signal=9, min_periods=None, append=True)
    rsi = ta.rsi(df[-points-14:]['close'], 14)

    # Bollinger Bands
    bb = ta.bbands(df[-points-20:]['close'], length=20, std=2, mamode='ema')
    bblow, bbmid, bbup = bb[bb.columns[0]], bb[bb.columns[1]], bb[bb.columns[2]]

    # добавление графиков к mpf https://github.com/matplotlib/mplfinance/blob/master/examples/addplot.ipynb
    apdict = [
        mpf.make_addplot(bbup[-points:], color='black'),
        mpf.make_addplot(bbmid[-points:], color='black'),
        mpf.make_addplot(bblow[-points:], color='black'),
        mpf.make_addplot(atr[-points:], panel=0, color='red'),
        mpf.make_addplot(vwap[-points:], color='blue'),
        mpf.make_addplot(macd[macd.columns[0]][-points:], panel=2, secondary_y=False),
        mpf.make_addplot(macd[macd.columns[2]][-points:], panel=2, linestyle='dotted', ylabel='MACD'),
        mpf.make_addplot(macd[macd.columns[1]][-points:], panel=2, secondary_y=False, type='bar'),
        mpf.make_addplot(rsi[-points:], panel=1, secondary_y=True, color='black'),
        ]

    # отрисовка.
    fig, ax = mpf.plot(
        df[-points:],
        type='candle',
        volume=True, 
        style=customstyle,
        figsize=(width_in_inches, height_in_inches),
        returnfig=True, # это надо, чтобы mpf.plot вернул fix, ax.
        # разворот подписей по оси X, т.к. в документации openai написано, что повернутый текст он плохо читает (наверное 
        # умышленно порезана модель, чтобы нельзя было ее использовать для распознавания капчи)
        xrotation=0, 
        #return_width_config=wconfig,
        update_width_config={'volume_width': 0.75, 'candle_width': 0.75, 'candle_linewidth': 1},
        addplot=apdict
        )

    ax[0].margins(x=0) # убрать отступы слева и справа на графике.

    # Сохранение графика с учетом изменений отступов
    print(f'Saving {image_path}...')
    fig.savefig(image_path, bbox_inches='tight', dpi=dpi)


# Function to encode the image
def encode_image(image_path):
  with open(image_path, "rb") as image_file:
    return base64.b64encode(image_file.read()).decode('utf-8')


def save_response(responses_dir, content, symbol, charts_at):
    symbol_responses_dir = f'{responses_dir}/{symbol}/'
    os.makedirs(symbol_responses_dir, exist_ok=True)
    # Текущая дата и время + pid для уникальности имени файла лога
    current_time = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    process_id = os.getpid()  # Получаем идентификатор текущего процесса
    charts_at_ = charts_at.replace(' ', '_')
    log_filename = f'{symbol_responses_dir}{charts_at_}__{current_time}__{process_id}.json'
    # Создаем лог данных
    log_data = {
        'symbol': symbol,
        'charts_at': charts_at,
        'content': content,
        'timestamp': current_time,
        'process_id': process_id,
    }
    # Сохраняем лог данных в JSON файл
    with open(log_filename, 'w') as json_file:
        json.dump(log_data, json_file, indent=4)
    print(f'Saved response to {log_filename}')


def save_response_md(responses_dir, content, symbol, charts_at):
    symbol_responses_dir = f'{responses_dir}/{symbol}/'
    os.makedirs(symbol_responses_dir, exist_ok=True)
    # Текущая дата и время + pid для уникальности имени файла лога
    current_time = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    process_id = os.getpid()  # Получаем идентификатор текущего процесса
    charts_at_ = charts_at.replace(' ', '_')
    log_filename = f'{symbol_responses_dir}{charts_at_}__{current_time}__{process_id}.md'
    # Сохраняем лог данных в JSON файл
    with open(log_filename, 'w') as json_file:
        json_file.write(content)
    print(f'Saved response markdown to {log_filename}')


def get_forecast_from_chart():
    # Getting the base64 string
    base64_image = encode_image(image_path)
    payload = {
        "model": "gpt-4o",
        "messages": [
            {
            "role": "system", 
            "content": "You are a professional quantitative analyst specializing in financial market analysis and price" 
                + " forecasting. You always spend a few sentences explaining background context, assumptions, and" 
                + " step-by-step thinking BEFORE you try to answer a question to ensure accuracy. You conduct a"
                + " thorough analysis of the overall market situation before providing forecasts."
            },
            {
            "role": "user", 
            "content": [
                {
                "type": "text", 
                "text": "Could you please analyze the attached minute candlestick chart and provide forecasts for the next"
                    + " 5 minutes. The main chart includes Bollinger Bands (period=20, color=black), VWAP (color=blue), ATR"
                    + " (period=10, color=red). The volume chart also includes RSI (period=14, color=black)."
                    + " Below the volume chart is a panel with MACD (fast=12, slow=26, signal=9). Please MAKE SURE TO"
                    + " INCLUDE the predicted CLOSING PRICE RANGE after the next 5 minutes as well as the PROBABILITIES of"
                    + " price increase and decrease and your CONFIDENCE in the forecast as a numerical value on a scale from 1 to 10."
                },
                {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_image}"
                },
                }
            ],
            }
        ],
        "max_tokens": 1000
    }

    print(f'Requesting analysis...')
    # делаем первый запрос к API, в котором просим провести анализ графика.
    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    j = response.json()

    # Извлечение значения поля content
    content = j['choices'][0]['message']['content']
    return content


def get_forecast_json_string(content):
    # делаем второй запрос к API, в котором просим предыдущий ответ оформить в виде json.

    payload = {
        "model": "gpt-3.5-turbo",# берем модель 3.5 турбо, т.к. она в 10 раз дешевле gpt-4o и с задачей справляется.
        "response_format": { "type": "json_object" },
        "messages": [
            {
            "role": "system", 
            "content": """You are an LLM assistant specialized in converting financial analysis text into structured JSON format. 
Your task is to extract key numerical values and probabilities from the provided analysis and format 
them into a JSON object with the following fields: 'h' for the predicted highest price, 'l' for the 
predicted lowest price, 'p_up' for the probability of price increase, 'p_down' for the probability 
of price decrease, 'conf' for the confidence in the forecast, and 'error' for any potential issues or 
discrepancies noted during extraction. 
Ensure the JSON output accurately reflects the information in the analysis, adheres to the following 
JSON Schema:
```
{
"$schema": "http://json-schema.org/draft-07/schema#",
"type": "object",
"properties": {
    "h": {
    "type": "number",
    },
    "l": {
    "type": "number",
    },
    "p_up": {
    "type": "number",
    "minimum": 0,
    "maximum": 100
    },
    "p_down": {
    "type": "number",
    "minimum": 0,
    "maximum": 100
    },
    "conf": {
    "type": "number",
    "minimum": 0,
    "maximum": 10
    },
    "error": {
    "type": "string",
    }
},
"additionalProperties": false
}
```
Respond only in JSON format without any additional text, as your response will be processed automatically by a program."""
            },
            {
            "role": "user", 
            "content": [
                {
                "type": "text", 
                "text": content
                }
            ],
            }
        ],
        "max_tokens": 1000
    }

    print(f'Requesting json...')
    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    j = response.json()

    json_string = j['choices'][0]['message']['content']
    return json_string


def append_forecast_to_csv(symbol, charts_at, data, current_time_string):
    forecasts_dir = 'forecasts/'
    os.makedirs(forecasts_dir, exist_ok=True)
    # Имя вашего CSV файла
    filename = f'{forecasts_dir}{symbol}.csv'
    print(f'Saving forecast into {filename}...')
    # Проверяем, существует ли файл
    file_exists = os.path.isfile(filename)

    # Открываем файл в режиме добавления или создания
    with open(filename, 'a', newline='') as file:
        writer = csv.writer(file)
        
        # Если файл не существует, пишем заголовок
        if not file_exists:
            header = [
                'last_candle_time',
                'high',
                'low',
                'p_up',
                'p_down',
                'conf',
                'created_at',
                'error',
            ]
            writer.writerow(header)
        
        forecast = (charts_at, data["h"], data['l'], data['p_up'], data['p_down'], data['conf'], current_time_string, data['error'])
        # Добавляем кортеж как новую строку
        writer.writerow(forecast)
    print(f"Прогноз успешно добавлен в файл {filename}")


def get_forecast(symbol, charts_at):
    """
    Получить прогноз для тикера в заданое время.
    
    symbol - например, BTCUSD.
    charts_at - строка в формате %Y-%m-%d %H:%M например '2024-01-13 01:02'
    """
    current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f'Reading {chart_period} data for {charts_at}...')
    df = get_df_for_chart(symbol, charts_at, chart_period)
    create_image(df)
    content = get_forecast_from_chart()
    # сохраняем ответ первого запроса к api в целях логирования, чтобы можно было потом при дебаге посмотреть что был за 
    # ответ от чата.
    save_response('api_responses_1', content, symbol, charts_at)
    save_response_md('api_responses_1_md', content, symbol, charts_at)
    json_string = get_forecast_json_string(content)
    # сохраняем ответ второго запроса к api
    save_response('api_responses_2', json_string, symbol, charts_at)

    # Преобразование строки JSON в объект Python (словарь)
    data = json.loads(json_string)

    print('Forecast:')
    print('time                     high            low             p_up    p_down  conf     created_at           error')
   #print('2024-05-29 08:35         67850           67750           55      45      5        2024-06-02-14-04-20')
    print(charts_at, ' \t', data["h"], ' \t', data['l'], ' \t', data['p_up'], ' \t', data['p_down'], ' \t', 
          data['conf'], ' \t', data['error'], current_time)

    append_forecast_to_csv(symbol, charts_at, data, current_time)
    return data

if __name__ == "__main__":
    get_forecast(
        symbol = 'BTCUSD', 
        charts_at = '2024-05-29 08:35' # время окончания графика
    )