import asyncio
import json
import redis.asyncio as aioredis

# Функция для чтения данных из Redis
async def view_data(redis, pattern):
    keys = await redis.keys(pattern)
    for key in keys:
        key = key.decode('utf-8')  # Декодирование ключа
        key_type = await redis.type(key)
        if key_type == b'list':
            # Используем LRANGE для получения всех элементов списка
            values = await redis.lrange(key, 0, -1)
            decoded_values = [json.loads(value.decode('utf-8')) for value in values]  # Декодирование значений
            print(f"{key}: {decoded_values}")
        else:
            print(f"Skipping key {key} of type {key_type.decode('utf-8')}")

# Основная функция для запуска задач
async def main():
    redis = aioredis.from_url('redis://localhost:6379')
    await view_data(redis, '*')

# Установка правильного событийного цикла для Windows
if __name__ == "__main__":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
