import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def test():
    engine = create_async_engine(
        "postgresql+asyncpg://reachy_dev:tweetwd4959@localhost:5432/reachy_emotion"
    )
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT version()"))
        print(result.scalar())

asyncio.run(test())