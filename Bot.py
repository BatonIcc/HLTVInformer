import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from config import Config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)
bot = Bot(token=Config.TOKEN)
dp = Dispatcher()

@dp.message(Command('start'))
async def start(message: types.Message):
    answer = f"Hello, {message.chat.first_name}.\nЭтот бот уведомляет о меропрятиях на HLTV\n/help - команды бота"
    await message.answer(answer)

@dp.message(Command('help'))
async def help(message: types.Message):
    answer = ("/help - команды бота\n/subscribe_team - подписаться на все мероприятиях, в которых участвует команда\n/subscribe_event - подписаться на меропрятие\n/events - ближайшие мероприятия\n/unsubscribe - отписаться от рассылки\n/profile - страница пользователя")
    await message.answer(answer)