import gspread
from oauth2client.service_account import ServiceAccountCredentials
from collections import defaultdict


def authenticate():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name('secret-api.json', scope)
    client = gspread.authorize(creds)
    return client


def get_sheet(client, sheet_id, sheet_name):
    sheet = client.open_by_key(sheet_id).worksheet(sheet_name)
    return sheet


def aggregate_records(records):
    aggregated_data = defaultdict(lambda: {
        'ID': None, 'Username': None, 'API_KEYS': None, 'payments': 0, 'comission': 0,
        'Unpaid_comission': 0, 'Last_payment_date': None, 'knive_algo': '2', 'sd_algo': '2',
        'correlation_algo': '2', 'comission_rate': '0.15'
    })

    for record in records:
        user_id = record['ID']
        user_data = aggregated_data[user_id]

        if user_data['ID'] is None:
            user_data['ID'] = record['ID']
        if user_data['Username'] is None:
            user_data['Username'] = record['Username']

        user_data['API_KEYS'] = record['API_KEYS']
        user_data['payments'] += int(record['payments']) if record['payments'] else 0
        user_data['comission'] += int(record['comission']) if record['comission'] else 0
        user_data['Unpaid_comission'] = user_data['comission'] - user_data['payments']

        if record['Last_payment_date']:
            user_data['Last_payment_date'] = record['Last_payment_date']

        if record['knive_algo']:
            user_data['knive_algo'] = record['knive_algo']

        if record['sd_algo']:
            user_data['sd_algo'] = record['sd_algo']

        if record['correlation_algo']:
            user_data['correlation_algo'] = record['correlation_algo']

        if record['comission_rate']:
            user_data['comission_rate'] = record['comission_rate']

    return list(aggregated_data.values())


def sort_sheet(sheet):
    records = sheet.get_all_records()

    # Собираем данные в словарь по пользователям, пропуская записи без ID
    user_data = defaultdict(list)
    for record in records:
        user_id = record.get('ID')
        if user_id:
            user_data[user_id].append(record)

    # Преобразуем ключи в строки для сортировки
    sorted_user_ids = sorted(user_data.keys(), key=lambda x: str(x))

    # Сортируем словарь по ID пользователей и собираем все записи в один список
    sorted_records = []
    for user_id in sorted_user_ids:
        user_records = user_data[user_id]
        sorted_records.extend(user_records)

    # Агрегируем данные для каждого пользователя
    aggregated_records = aggregate_records(sorted_records)

    return aggregated_records


def update_sorted_sheet(client, sheet_id, sorted_records, sorted_sheet_name):
    # Открываем лист для обновления отсортированными данными
    sorted_sheet = client.open_by_key(sheet_id).worksheet(sorted_sheet_name)

    # Очищаем лист и обновляем данными
    sorted_sheet.clear()
    if sorted_records:
        # Получаем заголовки из первой записи
        headers = list(sorted_records[0].keys())
        # Обновляем лист
        sorted_sheet.update([headers] + [list(record.values()) for record in sorted_records])
    print("Sorted sheet updated")


def main():
    client = authenticate()
    sheet_id = '1k6jHCTY2uUtDWfa8b0ryQhGqEAKnTLrdD_T2jUzJYmI'
    source_sheet_name = 'SclapiX'
    sorted_sheet_name = 'SclapiX_sorted'

    # Получаем лист с исходными данными
    source_sheet = get_sheet(client, sheet_id, source_sheet_name)

    # Сортируем данные и сохраняем их в переменной
    sorted_records = sort_sheet(source_sheet)

    # Обновляем отсортированные данные на другом листе
    update_sorted_sheet(client, sheet_id, sorted_records, sorted_sheet_name)


if __name__ == "__main__":
    main()
