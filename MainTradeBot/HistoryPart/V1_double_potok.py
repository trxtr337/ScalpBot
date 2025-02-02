import asyncio
import json
import websockets
import redis.asyncio as aioredis
from binance import AsyncClient
import keys
from datetime import datetime



#Нужно запускать#Нужно запускать#Нужно запускать#Нужно запускать#Нужно запускать#Нужно запускать



# Функция для создания клиента Binance
async def create_client():
    return await AsyncClient.create(keys.api_key, keys.api_secret)

# Функция для получения всех данных и записи в Redis
async def get_all_data(client, symbols, uri_id):
    uri = f"wss://fstream.binance.com/stream?streams="

    # Создаем список символов для подключения к веб-сокетам
    symbol_streams = [f"{symbol.lower()}@ticker" for symbol in symbols]
    stream_names = "/".join(symbol_streams)
    full_uri = uri + stream_names
    print(f'Websocket connection {uri_id} opened')

    redis = aioredis.from_url('redis://localhost:6354')

    async with websockets.connect(full_uri) as websocket:
        while True:
            try:
                response = await websocket.recv()
                data = json.loads(response)
                symbol = data["stream"].split("@")[0]
                ticker_info = data["data"]
                await adaptation_of_information_about_tickers(ticker_info, symbol, redis)
            except websockets.exceptions.ConnectionClosed:
                print(f"Connection {uri_id} closed. Reconnecting...")
                await get_all_data(client, symbols, uri_id)
            except Exception as e:
                print(f"Error occurred in connection {uri_id}: {e}")
                print(f"Connection {uri_id} closed. Reconnecting...")
                await get_all_data(client, symbols, uri_id)

# Функция для адаптации информации о тикерах и записи в Redis
async def adaptation_of_information_about_tickers(ticker_info, symbol, redis):
    current_price = float(ticker_info["c"])
    current_time = datetime.now()

    key = symbol
    timestamp = int(current_time.timestamp() * 1000)
    value = {'timestamp': timestamp, 'price': current_price}

    # Добавляем новые данные в список в Redis
    await redis.rpush(key, json.dumps(value))
    print(f"Stored data for {symbol} at {current_time}: {current_price}")

# Основная функция для запуска задач
async def main():
    client = await create_client()
    tickers = await client.futures_ticker()
    all_symbols = [ticker['symbol'] for ticker in tickers]

    # Разделяем символы на две группы
    mid_index = len(all_symbols) // 2
    symbols_group1 = all_symbols[:mid_index]
    symbols_group2 = all_symbols[mid_index:]

    # Запускаем две задачи для двух групп символов
    await asyncio.gather(
        get_all_data(client, symbols_group1, 1),
        get_all_data(client, symbols_group2, 2)
    )

# Установка правильного событийного цикла для Windows
if __name__ == "__main__":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
