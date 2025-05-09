from Bot import bot, dp
import asyncio

async def main():
    await dp.start_polling(bot)

def job():
    pass

if __name__ == "__main__":
    asyncio.run(main())