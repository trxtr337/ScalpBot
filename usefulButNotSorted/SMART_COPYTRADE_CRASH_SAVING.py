import time
import asyncio
import json
import websockets
import requests
import hashlib
import hmac
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_DOWN
import gspread
from google.oauth2.service_account import Credentials
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
def precision_Upd():
    global okrug
    url = 'https://fapi.binance.com/fapi/v1/exchangeInfo'

    try:
        response = requests.get(url)
        response_data = response.json()

        steps = {}

        temp_steps = response_data['symbols']
        for symbol_data in temp_steps:
            symbol = symbol_data['symbol']

            filters = symbol_data['filters']
            for filter_data in filters:
                if filter_data['filterType'] == 'LOT_SIZE':
                    step = float(filter_data['stepSize'])
                    steps[symbol] = step

        okrug=steps

    except Exception as e:
        print('Error fetching data:', e)


precision_Upd()

print(okrug)
GG=1
RESTART_INTERVAL = 1 * 60
# Your JSON key file path
json_keyfile_path = "C:\\Users\\vadik\\Downloads\\sheet-editor-394715-4dca498b2d07.json"
# Authenticate with the JSON key
creds = Credentials.from_service_account_file(json_keyfile_path, scopes=["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])
client = gspread.authorize(creds)
# Declare the variables as global
User = None
user_id = None
Username = None
API_KEY = None
SECRET_KEY = None
Trading_volume = None
# URL Binance API
BASE_URL = 'https://fapi.binance.com'
# Now the 'data' dictionary is ready with the key-value pairs as given.
processed_trade_ids = set()
side_list = ['']
quantity_list = []
price_list = []
# Пример использования функции для записи данных в таблицу
data_to_write = []


def get_filtered_rows(spreadsheet_url, sheet_index):
    global User, user_id, Username, API_KEY, SECRET_KEY, Trading_volume
    # Open Google Sheets document by URL
    spreadsheet = client.open_by_url(spreadsheet_url)
    worksheet = spreadsheet.get_worksheet(sheet_index)

    # Get all values from the sheet
    all_values = worksheet.get_all_values()

    # Find column indices
    header_row = all_values[0]
    id_column_index = header_row.index('ID')
    username_column_index = header_row.index('Username')
    api_keys_column_index = header_row.index('API_KEYS')
    trading_volume_column_index = header_row.index('Trading_volume')
    unpaid_comission_column_index = header_row.index('Unpaid_comission')
    last_payment_date_column_index = header_row.index('Last_payment_date')

    # List to store filtered rows
    filtered_rows = []

    # Current date and time
    current_datetime = datetime.now()

    # Iterate through rows and filter data
    for row in all_values[1:]:
        current_id = row[id_column_index]
        current_username = row[username_column_index]
        current_api_keys = row[api_keys_column_index]
        current_trading_volume = row[trading_volume_column_index]
        current_unpaid_comission = row[unpaid_comission_column_index]
        current_last_payment_date_str = row[last_payment_date_column_index]

        if current_id and current_username and len(current_api_keys.strip()) == 129 and Decimal(current_trading_volume) >= 100:
            # Check if Last_payment_date is not empty
            if current_last_payment_date_str:
                # Convert the Last_payment_date to a datetime object
                current_last_payment_date = datetime.strptime(current_last_payment_date_str, "%Y-%m-%d %H:%M:%S")

                # Calculate the difference in days
                days_difference = (current_datetime - current_last_payment_date).days

                # Check the conditions for date comparison and Unpaid_comission value
                if Decimal(current_unpaid_comission) <= 5:
                    filtered_rows.append(row)
                elif days_difference <= 5:
                    filtered_rows.append(row)
            else:
                filtered_rows.append(row)

    return filtered_rows

def main_program():
    global User, user_id, Username, API_KEY, SECRET_KEY, Trading_volume
    spreadsheet_url = "https://docs.google.com/spreadsheets/d/1n3Vq1Q4q9QXCpjJSh-SGbiBaJwpW1u8wFYPkIjUOB40/edit#gid=0"
    sheet_index = 0  # Index of the sheet (0 indicates the first sheet)
    filtered_rows = get_filtered_rows(spreadsheet_url, sheet_index)

    # Ваш код для дальнейшей обработки отфильтрованных рядов
    User = filtered_rows[GG]
    user_id = filtered_rows[GG][0]
    Username = filtered_rows[GG][1]
    api_keys= filtered_rows[GG][2].split()
    API_KEY = api_keys[0] if api_keys else ''
    SECRET_KEY = api_keys[1] if len(api_keys) > 1 else ''
    Trading_volume=filtered_rows[GG][6]
    print(user_id, Username, API_KEY, SECRET_KEY, Trading_volume)

def refresh_program():
    global User, user_id, Username, API_KEY, SECRET_KEY, Trading_volume
    # Execute main_program() once manually to get initial values
    main_program()

    scheduler = BackgroundScheduler(timezone=pytz.utc)
    scheduler.add_job(main_program, 'cron', minute='1,21,41')
    scheduler.start()

    try:
        while True:
            pass
    except KeyboardInterrupt:
        scheduler.shutdown()

async def write_data_to_sheet(data):
    global data_to_write
    # Путь к JSON-ключу авторизации
    json_keyfile_path = "C:\\Users\\vadik\\Downloads\\sheet-editor-394715-4dca498b2d07.json"

    # Аутентификация через JSON-ключ
    creds = Credentials.from_service_account_file(json_keyfile_path, scopes=["https://spreadsheets.google.com/feeds",
                                                                             "https://www.googleapis.com/auth/drive"])
    client = gspread.authorize(creds)

    # URL таблицы, куда будем записывать данные
    spreadsheet_url = "https://docs.google.com/spreadsheets/d/1n3Vq1Q4q9QXCpjJSh-SGbiBaJwpW1u8wFYPkIjUOB40/edit#gid=0"

    try:
        # Открываем таблицу по URL
        sheet = client.open_by_url(spreadsheet_url)

        # Выбираем лист, куда будем записывать данные (можно использовать по индексу или названию)
        worksheet = sheet.get_worksheet(0)  # 0 - это индекс листа (первый лист)

        # Записываем данные в таблицу
        # В данном примере считаем, что данные представлены в виде списка списков,
        # где каждый внутренний список представляет одну строку данных.
        for row_data in data:
            worksheet.append_row(row_data)

        print("Данные успешно записаны в таблицу.")
        data_to_write = []


    except Exception as e:
        print(f"Произошла ошибка при записи данных: {e}")





# Функция для подписи запроса
def generate_signature(query_string):
    return hmac.new(SECRET_KEY.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()


# Функция для выполнения POST-запросов к Binance API
def binance_post_request(endpoint, params=None):
    if params is None:
        params = {}
    query_string = '&'.join([f'{k}={v}' for k, v in params.items()])
    signature = generate_signature(query_string)
    url = f'{BASE_URL}{endpoint}?signature={signature}'

    try:
        response = requests.post(url, headers={'X-MBX-APIKEY': API_KEY}, data=params, timeout=2)
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response.json()
    except requests.exceptions.Timeout:
        print("Request timeout")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
        return None

# Открытие позиции по рынку
async def create_market_order(symbol, side, price, Y):
    global quantity_list, price_list, Trading_volume, data_to_write
    endpoint = '/fapi/v1/order'
    volume =0.1*float(Trading_volume)
    if side_list[-1] != side:
        side_list.append(side)
        decimal_places = len(str(Y).split('.')[1]) if '.' in str(Y) else 0
        quantity_raschet = (Decimal(volume) / Decimal(price)).quantize(Decimal('1e-{0}'.format(decimal_places)),
                                                                       rounding=ROUND_DOWN)
        quantity_list.append(quantity_raschet)
        quantity_list = quantity_list[-2:]
        price_list.append(price)
        price_list = price_list[-2:]
        if side == 'SELL':
            print(price_list)
            a = price_list[-1]
            b = price_list[-2]
            change = ((a - b) / a)
            trade = volume * change
            if trade > 0:
                comission = trade * 0.15

                data_to_write.append([user_id, Username, None, None, comission])
                await write_data_to_sheet(data_to_write)
                print(comission)
        # print(quantity_list)
        quantity = quantity_list[-2] if side == 'SELL' else quantity_list[-1]
        print('------------', symbol, side, price, Y, quantity, '------------')
        params = {
            'symbol': symbol,
            'side': side,
            'positionSide': 'BOTH',
            'type': 'MARKET',
            'quantity': quantity,
            'timestamp': int(time.time() * 1000)
        }
        response = binance_post_request(endpoint, params)
        return response


async def precision(symbol, side, price):
    if symbol in okrug:
        Y = okrug[symbol]
        # print('символ найден')
        await create_market_order(symbol, side, price, Y)
    # print ('символ не найден')


async def on_message(message):
    data = json.loads(message)
    if 'e' in data and data['e'] == 'ORDER_TRADE_UPDATE' and data['o'].get('x') == 'TRADE':
        trade_id = data['o'].get('t')
        if trade_id is not None and trade_id not in processed_trade_ids:
            processed_trade_ids.add(trade_id)

            symbol = data['o']['s']
            side = data['o']['S']
            price = float(data['o']['ap'])

            # print("New filled order trade:")
            # print(symbol, side, price)
            # print(data)
            await precision(symbol, side, price)


async def connect():
    # Замените YOUR_API_KEY на ваш собственный ключ API Binance
    api_key = "mYEEydsfLJWa5MhbWiLo2kN7HthG6didbTWLyp63IZGRbM4q7ZW00XacHwvSl6wI"

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



def main():
    # Get filtered rows from the spreadsheet
    spreadsheet_url = "https://docs.google.com/spreadsheets/d/1n3Vq1Q4q9QXCpjJSh-SGbiBaJwpW1u8wFYPkIjUOB40/edit#gid=0"
    sheet_index = 0
    filtered_rows = get_filtered_rows(spreadsheet_url, sheet_index)

    if not filtered_rows:
        print("No valid data found in the spreadsheet.")
        return

    # Execute the main_program() with the first filtered row
    global GG
    GG = 1
    main_program()

    scheduler = BackgroundScheduler(timezone=pytz.utc)
    scheduler.add_job(main_program, 'cron', minute='13,33,53')
    scheduler.start()

    try:
        while True:
            # Start connecting to the WebSocket and running the trading strategy
            asyncio.get_event_loop().run_until_complete(connect())
    except KeyboardInterrupt:
        scheduler.shutdown()

def run_code_with_timer(code_to_run, retry_interval=5, max_retries=None):
    retries = 0
    while max_retries is None or retries < max_retries:
        try:
            exec(code_to_run)
            break
        except Exception as e:
            print(f"Ошибка: {e}")
            print(f"Запуск кода будет повторен через {retry_interval} секунд...")
            time.sleep(retry_interval)
            retries += 1
    else:
        print(f"Превышено максимальное количество попыток ({max_retries}). Программа завершается.")

if __name__ == "__main__":
    python_code = """
asyncio.run(main())
"""

    run_code_with_timer(python_code, retry_interval=RESTART_INTERVAL)