import asyncio
import json
import websockets
import requests
from telegram import Bot
from telegram.ext import Updater, CommandHandler
from telegram.error import TelegramError
from chat_id_list import chat_ids


# Замените 'YOUR_BOT_TOKEN' на ваш полученный токен
bot = Bot(token='6292686194:AAEF4_c5E83Gq-xs0O9XM2HJxNpkMmOFBKo')
# Now the 'data' dictionary is ready with the key-value pairs as given.
processed_trade_ids = set()
# URL Binance API
BASE_URL = 'https://fapi.binance.com'
price_list = []





async def on_message(message):
    data = json.loads(message)
    if 'e' in data and data['e'] == 'ORDER_TRADE_UPDATE' and data['o'].get('x') == 'TRADE':
        trade_id = data['o'].get('t')
        if trade_id is not None and trade_id not in processed_trade_ids:
            processed_trade_ids.add(trade_id)
            price_list=[]
            symbol = data['o']['s']
            side = data['o']['S']
            price = float(data['o']['ap'])
            price_list.append(price)
            if len(price_list)==2:
                a = price_list[-1]
                b = price_list[-2]
                change = ((a - b) / a)*100
                await send_information_closed_trade(a,b,side,symbol,change) and price_list.clear()

            else:
                a = price_list[-1]
                await send_information_opened_trade(a,side,symbol)

async def send_information_opened_trade(price, side, symbol):
    global chat_ids
    message = f"Открыт новый {side} трейд на паре {symbol}. Цена: {price}"
    try:
        for chat_id in chat_ids:
            bot.send_message(chat_id=chat_id, text=message)
    except TelegramError as e:
        print("Ошибка при отправке рассылки:", e)


async def send_information_closed_trade(a, b, side, symbol, change):
    global chat_ids
    message = f"Закрыт трейд на паре {symbol}. Цена при открытии: {b}, цена при закрытии: {a}. Изменение: {change:.2%}"
    try:
        for chat_id in chat_ids:
            bot.send_message(chat_id=chat_id, text=message)
    except TelegramError as e:
        print("Ошибка при отправке рассылки:", e)

async def connect():
    # Замените YOUR_API_KEY на ваш собственный ключ API Binance
    api_key = "G9fAfJiLwsGfpd17F5zfbZCLsqaHbysbc4WYhoy7END6EjIcgCWReYSohZfxjnMy"

    # Получаем новый listenKey
    listen_key_url = f"https://fapi.binance.com/fapi/v1/listenKey"
    headers = {
        "X-MBX-APIKEY": api_key
    }
    response = requests.post(listen_key_url, headers=headers)
    listen_key = response.json()['listenKey']

    websocket_url = f"wss://fstream.binance.com/ws/{listen_key}"
    async with websockets.connect(websocket_url) as ws:
        print("Connection opened")
        async for message in ws:
            await on_message(message)

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(connect())
