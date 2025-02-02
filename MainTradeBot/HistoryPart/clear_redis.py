import redis.asyncio as aioredis
import asyncio

#Нужно запускать#Нужно запускать#Нужно запускать#Нужно запускать#Нужно запускать
#Первым

async def clear_redis():
    redis = aioredis.from_url('redis://localhost:6354')
    await redis.flushdb()
    print("All keys have been deleted.")

asyncio.run(clear_redis())
