import asyncio
import json
import redis.asyncio as aioredis
import pandas as pd
import matplotlib.pyplot as plt
import mplfinance as mpf

async def fetch_data_from_redis(redis, symbol):
    # Извлечение данных для заданного символа из Redis
    values = await redis.lrange(symbol, 0, -1)
    data = [json.loads(value) for value in values]
    return data

def create_candlesticks(data, interval):
    df = pd.DataFrame(data)
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)

    ohlc_dict = {
        'price': 'ohlc'
    }
    resampled_df = df.resample(interval).apply(ohlc_dict)
    resampled_df.columns = ['open', 'high', 'low', 'close']

    # Заполнение пропущенных значений
    resampled_df = resampled_df.ffill()

    return resampled_df

def plot_candlesticks(candlesticks, symbol, interval):
    mpf.plot(candlesticks, type='candle', title=f"{interval} Candlesticks for {symbol}", style='charles')

async def process_candlesticks(redis, symbol, intervals):
    data = await fetch_data_from_redis(redis, symbol)
    for interval in intervals:
        candlesticks = create_candlesticks(data, interval)
        print(f"{interval} Candlesticks for {symbol}:")
        print(candlesticks)
        if interval == '1min':
            plot_candlesticks(candlesticks, symbol, interval)

async def main():
    redis = aioredis.from_url('redis://localhost:6354')
    symbols = ['1000pepeusdt', 'icxusdt', 'ldousdt']  # Замените на ваши символы
    intervals = ['1min', '5min', '1s']

    tasks = []
    for symbol in symbols:
        tasks.append(process_candlesticks(redis, symbol, intervals))

    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
