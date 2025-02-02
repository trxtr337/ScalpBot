
import redis
import time
import random

# Подключение к Redis
redis_host = 'localhost'
redis_port = 6354 # Обновленный порт
stream_name = 'Signals'

# Создание клиента Redis
r = redis.Redis(host=redis_host, port=redis_port)

# Возможные стратегии и параметры сигналов
strategies = ['KN', 'SD', 'CR']
symbols = ['BTCUSDT', 'ETHUSDT']
sides = ['buy', 'sell']
quantity = 0.001

def send_signal():
    signal = {
        'symbol': random.choice(symbols),
        'side': random.choice(sides),
        'quantity': quantity,
        'strategy': random.choice(strategies)
    }
    r.xadd(stream_name, signal)
    print(f"Sent signal: {signal}")

def main():
    while True:
        send_signal()
        sleep_time = random.randint(10, 30)
        time.sleep(sleep_time)

if __name__ == "__main__":
    main()
