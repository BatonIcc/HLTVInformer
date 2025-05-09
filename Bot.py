import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from config import Config

logging.basicConfig(level=logging.INFO)
bot = Bot(token=Config.TOKEN)
dp = Dispatcher()

@dp.message(Command('start'))
async def start(message: types.Message):
    message.reply_markup.to_python().keys()
    answer = f"Hello, {message['from']['first_name']}.\nFrom HLTVInformer"
    await message.answer(answer)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())