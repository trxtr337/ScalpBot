import redis
import json
import random


# Подключение к Redis
redis_host = 'localhost'
redis_port = 6354 # Обновленный порт
stream_name = 'Signals'
consumer_group = f'trade_group_{random.randint(100000000, 999999999)}'  # Использование случайного 9-значного числа для группы
consumer_name = f'consumer_{random.randint(100000000, 999999999)}'  # Использование случайного 9-значного числа для потребителя

# Создание клиента Redis
r = redis.Redis(host=redis_host, port=redis_port)

# Создание группы потребителей только в случае её отсутствия
def create_consumer_group():
    try:
        r.xgroup_create(stream_name, consumer_group, id='0', mkstream=True)
        print(f"Group {consumer_group} created.")
    except redis.exceptions.ResponseError as e:
        if "BUSYGROUP Consumer Group name already exists" in str(e):
            print(f"Group {consumer_group} already exists.")
        else:
            print(f"Error creating group: {e}")

create_consumer_group()

def main():
    while True:
        try:
            messages = r.xreadgroup(consumer_group, consumer_name, {stream_name: '>'}, count=10, block=5000)
            for message in messages:
                for msg in message[1]:
                    message_id = msg[0]
                    signal = msg[1]
                    print(f"Received signal: {signal}")
                    # Подтверждение получения сообщения
                    r.xack(stream_name, consumer_group, message_id)
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
