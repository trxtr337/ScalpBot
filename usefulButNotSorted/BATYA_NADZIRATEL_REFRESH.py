import gspread
from google.oauth2.service_account import Credentials
from decimal import Decimal, ROUND_DOWN
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
import pytz  # Добавьте эту строку для использования pytz
# Your JSON key file path
json_keyfile_path = "C:\\Users\\vadik\\OneDrive\\Рабочий стол\\ReliaTrade_Bot\\sheet-editor-394715-4dca498b2d07.json"

# Authenticate with the JSON key
creds = Credentials.from_service_account_file(json_keyfile_path, scopes=["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])
client = gspread.authorize(creds)

def update_unique_users_payments(spreadsheet_url, sheet_index):
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
    payments_column_index = header_row.index('payments')
    comission_column_index = header_row.index('comission')
    trading_volume_column_index = header_row.index('Trading_volume')
    last_payment_date_column_index = header_row.index('Last_payment_date') if 'Last_payment_date' in header_row else None

    # Add Unpaid_comission column if not present
    unpaid_comission_column_index = header_row.index('Unpaid_comission') if 'Unpaid_comission' in header_row else None
    if unpaid_comission_column_index is None:
        header_row.append('Unpaid_comission')
        unpaid_comission_column_index = len(header_row) - 1

    # Dictionary to store data for each unique ID, including Trading_volume and Last_payment_date
    id_data = {}

    # Iterate through rows and group data by unique ID
    for row in all_values[1:]:
        current_id = row[id_column_index]
        current_username = row[username_column_index]
        current_api_keys = row[api_keys_column_index]
        current_payment = row[payments_column_index]
        current_commission = row[comission_column_index]
        current_trading_volume = row[trading_volume_column_index]
        current_last_payment_date = row[last_payment_date_column_index] if last_payment_date_column_index is not None else None

        try:
            current_payment = Decimal(current_payment)
        except:
            current_payment = Decimal('0')

        try:
            current_commission = Decimal(current_commission)
        except:
            current_commission = Decimal('0')

        try:
            if current_trading_volume.strip():
                current_trading_volume = Decimal(current_trading_volume.strip())
            else:
                current_trading_volume = id_data.get(current_id, {}).get('trading_volume', Decimal('0'))
        except Exception as e:
            print(current_trading_volume)
            current_trading_volume = Decimal('0')
            print("The error is: ", e)

        # Update data for each ID
        if current_id in id_data:
            id_data[current_id]['payment'] += current_payment
            id_data[current_id]['commission'] += current_commission
            if current_api_keys:
                id_data[current_id]['api_keys'] = current_api_keys
            id_data[current_id]['trading_volume'] = current_trading_volume
            if current_last_payment_date:
                last_date = max(current_last_payment_date, id_data[current_id]['last_payment_date'])
                id_data[current_id]['last_payment_date'] = last_date
        else:
            id_data[current_id] = {
                'username': current_username,
                'api_keys': current_api_keys,
                'payment': current_payment,
                'commission': current_commission,
                'trading_volume': current_trading_volume,
                'last_payment_date': current_last_payment_date
            }

    # Delete all rows except the header
    worksheet.delete_rows(2, worksheet.row_count)

    # Create a new table with combined values for each unique ID
    for user_id, data in id_data.items():
        unpaid_commission = data['commission'] - data['payment']
        # Round the values to two decimal places
        payment_rounded = data['payment'].quantize(Decimal('0.00'), rounding=ROUND_DOWN)
        commission_rounded = data['commission'].quantize(Decimal('0.000'), rounding=ROUND_DOWN)
        unpaid_commission_rounded = unpaid_commission.quantize(Decimal('0.000'), rounding=ROUND_DOWN)
        new_row = [user_id, data['username'], data['api_keys'], str(payment_rounded), str(commission_rounded), str(unpaid_commission_rounded), str(data['trading_volume']), data['last_payment_date']]
        worksheet.append_row(new_row)

def get_filtered_rows(spreadsheet_url, sheet_index):
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
                if Decimal(current_unpaid_comission) <= 5 and days_difference <= 5:
                    filtered_rows.append(row)
            else:
                filtered_rows.append(row)

    return filtered_rows


# Example usage:
spreadsheet_url = "https://docs.google.com/spreadsheets/d/1n3Vq1Q4q9QXCpjJSh-SGbiBaJwpW1u8wFYPkIjUOB40/edit#gid=0"
sheet_index = 0  # Index of the sheet (0 indicates the first sheet)

# Вызываем первую функцию для обновления данных в таблице
update_unique_users_payments(spreadsheet_url, sheet_index)

# Вызываем вторую функцию для получения отфильтрованных рядов
filtered_rows = get_filtered_rows(spreadsheet_url, sheet_index)
#print(filtered_rows)
def main_program():
    # Example usage:
    spreadsheet_url = "https://docs.google.com/spreadsheets/d/1n3Vq1Q4q9QXCpjJSh-SGbiBaJwpW1u8wFYPkIjUOB40/edit#gid=0"
    sheet_index = 0  # Index of the sheet (0 indicates the first sheet)

    # Вызываем первую функцию для обновления данных в таблице
    update_unique_users_payments(spreadsheet_url, sheet_index)

    # Вызываем вторую функцию для получения отфильтрованных рядов
    filtered_rows = get_filtered_rows(spreadsheet_url, sheet_index)
    print('Количество включенных аккаунтов:',len(filtered_rows))

def refresh_program():
    scheduler = BackgroundScheduler(timezone=pytz.utc)  # Используйте pytz.utc
    scheduler.add_job(main_program, 'cron', minute='12,32,52')
    scheduler.start()

    try:
        while True:
            pass
    except KeyboardInterrupt:
        scheduler.shutdown()

if __name__ == "__main__":
    refresh_program()
