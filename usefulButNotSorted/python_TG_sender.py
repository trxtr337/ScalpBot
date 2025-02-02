from telegram import Bot
from telegram.ext import Updater, CommandHandler
from telegram.error import TelegramError
import time

# Замените 'YOUR_BOT_TOKEN' на ваш полученный токен
bot = Bot(token='6292686194:AAEF4_c5E83Gq-xs0O9XM2HJxNpkMmOFBKo')

def send_hello(update, context):
    chat_id = update.effective_chat.id
    message = "Привет! Я ваш бот. Как я могу помочь?"
    context.bot.send_message(chat_id=chat_id, text=message)

def send_broadcast(context):
    chat_ids = [10109173]
    message = "Это сообщение будет отправлено всем пользователям."

    try:
        for chat_id in chat_ids:
            context.bot.send_message(chat_id=chat_id, text=message)
    except TelegramError as e:
        print("Ошибка при отправке рассылки:", e)

if __name__ == "__main__":
    updater = Updater(token='6292686194:AAEF4_c5E83Gq-xs0O9XM2HJxNpkMmOFBKo', use_context=True)
    dispatcher = updater.dispatcher

    start_handler = CommandHandler('start', send_hello)
    dispatcher.add_handler(start_handler)

    interval_seconds = 30
    updater.start_polling()

    while True:
        send_broadcast(dispatcher.bot)
        time.sleep(interval_seconds)
