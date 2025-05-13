from aiogram import Bot, Dispatcher, types, F
from aiogram.filters.command import Command
from config import Config
from models import DatabaseManager
from kbs import *
from logger import logger
from datetime import timedelta, datetime

bot = Bot(token=Config.TOKEN)
dp = Dispatcher()
db_manager = DatabaseManager(Config.SQLALCHEMY_DATABASE_URI)

@dp.message(Command('start'))
async def start(message: types.Message):
    logger.info(f"start called by {message.from_user.id}")
    db_manager.create_user(message.from_user.id)
    answer = f"Привет, {message.from_user.first_name}.\nЭтот бот уведомляет о меропрятиях на HLTV"
    await message.answer(answer, reply_markup=basic_kb())

@dp.callback_query(F.data == "base")
async def base(callback: types.CallbackQuery):
    logger.info(f"start called by {callback.from_user.id}")
    answer = f"Привет, {callback.from_user.first_name}.\nЭтот бот уведомляет о меропрятиях на HLTV"
    await callback.message.edit_text(answer, reply_markup=basic_kb())

@dp.callback_query(F.data == "to_base")
async def to_base(callback: types.CallbackQuery):
    logger.info(f"to_base called by {callback.from_user.id}")
    await start(callback.message)

@dp.callback_query(F.data == 'all_events')
async def all_events(callback: types.CallbackQuery, page=0):
    logger.info(f"all_events called by {callback.from_user.id}")
    try:
        events = db_manager.get_all_events()
        if not events:
            await callback.answer("Турниры не найдены")
            return

        answer = "<b>Все турниры:</b>"
        events_d = {}
        for event in events:
            events_d[event.id] = {
                'message': event.name,
                'prefix': 'event-s'
            }

        await callback.message.edit_text(answer,
                                         reply_markup=enum_call_kb(events_d, page=page, kb_on_page=6),
                                         parse_mode='HTML')

    except Exception as e:
        logger.error(f"get all_events error {e}")
        await callback.answer("Произошла ошибка при получении списка турниров")

@dp.callback_query(F.data == 'all_teams')
async def all_teams(callback: types.CallbackQuery, page=0):
    logger.info(f"all_teams called by {callback.from_user.id}")
    try:
        teams = db_manager.get_all_teams()
        if not teams:
            await callback.answer("Команды не найдены")
            return

        answer = "<b>Все команды:</b>"
        teams_d = {}
        for team in teams:
            teams_d[team.id] = {
                'message': team.name,
                'prefix': 'team-s'
            }

        await callback.message.edit_text(answer,
                                         reply_markup=enum_call_kb(teams_d, page=page, kb_on_page=6),
                                         parse_mode='HTML')

    except Exception as e:
        logger.error(f"get all_teams error {e}")
        await callback.answer("Произошла ошибка при получении списка команд")

@dp.callback_query(F.data.startswith("_"))
async def change_page(callback: types.CallbackQuery):
    logger.info(f"change_page called by {callback.from_user.id}")
    funk, command, page = callback.data[1:].split('_')
    if 'event' in funk:
        await all_events(callback, int(page) + (1 if command == 'forward' else -1))
    elif 'team' in funk:
        await all_teams(callback, int(page) + (1 if command == 'forward' else -1))

@dp.callback_query(F.data.startswith("sub_"))
async def subscribe(callback: types.CallbackQuery):
    logger.info(f"subscribe called by {callback.from_user.id}")
    _, sub_to, id = callback.data.split('_')
    name = ''
    if sub_to == 'event':
        name = db_manager.subscribe_user_to_event(callback.from_user.id, int(id))
    elif sub_to == 'team':
        name = db_manager.subscribe_user_to_team(callback.from_user.id, int(id))

    if name:
        await callback.answer(f"Вы подписались на все матчи {name}")
    else:
        await callback.answer(f"Произошла ошибка")

@dp.callback_query(F.data.startswith("unsub_"))
async def unsubscribe(callback: types.CallbackQuery):
    logger.info(f"unsubscribe called by {callback.from_user.id}")
    _, unsub_from, id = callback.data.split('_')
    name = ''
    if unsub_from == 'event':
        name = db_manager.unsubscribe_user_from_event(callback.from_user.id, int(id))
    elif unsub_from == 'team':
        name = db_manager.unsubscribe_user_from_team(callback.from_user.id, int(id))

    if name:
        await callback.answer(f"Вы отписались от матчей")
    else:
        await callback.answer(f"Произошла ошибка")

@dp.callback_query(F.data.startswith("data_"))
async def show_data(callback: types.CallbackQuery):
    logger.info(f"change_page called by {callback.from_user.id}")
    _, prefix, id = callback.data.split('_')
    answer = '.'
    call_back_sub = '.'
    call_back_back = 'base'
    timezone = timedelta(hours=db_manager.get_timezone(callback.from_user.id))
    if 'event' in prefix:
        event = db_manager.get_event_by_id(int(id))
        start_date = (event.start_date + timezone).strftime('%d.%m.%Y') if event.start_date else 'дата не указана'
        end_date = (event.end_date + timezone).strftime('%d.%m.%Y') if event.end_date else 'дата не указана'
        answer = f'<b>{event.name}</b>\n{start_date} - {end_date}'
        call_back_sub = f'sub_event_{event.id}' if prefix[-1] == 's' else f'unsub_event_{event.id}'
        call_back_back = 'all_events' if prefix[-1] == 's' else 'show_sub_events'
    elif 'team' in prefix:
        team = db_manager.get_team_by_id(int(id))
        answer = f'<b>{team.name}</b>'
        call_back_sub = f'sub_team_{team.id}' if prefix[-1] == 's' else f'unsub_team_{team.id}'
        call_back_back = 'all_teams' if prefix[-1] == 's' else 'show_sub_teams'
    await callback.message.edit_text(answer, reply_markup=sub_kb(call_back_sub, call_back_back), parse_mode='HTML')

@dp.callback_query(F.data == 'my_matches')
async def my_matches(callback: types.CallbackQuery):
    logger.info(f"my_matches called by {callback.from_user.id}")
    try:
        matches = db_manager.get_matches_for_user(callback.from_user.id)
        if not matches:
            await callback.answer("Матчи не найдены")
            return

        timezone = timedelta(hours=db_manager.get_timezone(callback.from_user.id))

        matches_sorted = sorted(
            matches,
            key=lambda m: (
                (m.start_time + timezone)
                if m.start_time
                else datetime.min
            )
        )

        answer = "<b>Ближайшие матчи:</b>\n\n"

        for match in matches_sorted:
            start_time = (match.start_time + timezone).strftime('%d-%m-%Y %H:%M') if match.start_time else 'уже начался'
            line = f"• <b>{match.event.name}</b>\n{' - '.join([team.name for team in match.teams])}\n{start_time}\n\n"

            if len(answer + line) >= 4096:
                await callback.message.answer(answer, parse_mode='HTML', reply_markup=back_kb('to_base'))
                answer = ""
            answer += line

        if answer:
            await callback.message.answer(answer, parse_mode='HTML', reply_markup=back_kb('to_base'))

    except Exception as e:
        logger.error(f"get my_matches error {e}")
        await callback.answer("Произошла ошибка при получении списка ближайших событий.")

@dp.callback_query(F.data == 'profile')
async def profile(callback: types.CallbackQuery):
    logger.info(f"callback called by {callback.from_user.id}")
    time_zone = db_manager.get_timezone(callback.from_user.id)
    time_zone = str(time_zone) if time_zone < 0 else '+' + str(time_zone)
    await callback.message.edit_text(f"/time_zone <число> - установить часовой пояс\nтекущий часовой пояс: {time_zone}\nПодписки: ", reply_markup=subscribe_kb())

@dp.message(Command('time_zone'))
async def time_zone(message: types.Message):
    logger.info(f"time_zone called by {message.from_user.id}")
    timezone = message.text.split()[1]
    if timezone.isdigit():
        if db_manager.set_timezone(message.from_user.id, int(timezone)):
            await message.answer("часовой пояс успешно установлен")
            return
    await message.answer("произошла ошибка")

@dp.callback_query(F.data.startswith("show_sub_"))
async def show_subscribes(callback: types.CallbackQuery):
    logger.info(f"show_subscribes called by {callback.from_user.id}")
    _, _, prefix = callback.data.split('_')
    _d = {}
    sub_name = 'турниры' if prefix == 'events' else 'команды'
    if prefix == 'events':
        events = db_manager.get_user_subscribed_events(callback.from_user.id)
        for event in events:
            _d[event.id] = {
                'message': event.name,
                'prefix': 'event-u'
            }
    elif prefix == 'teams':
        teams = db_manager.get_user_subscribed_teams(callback.from_user.id)
        for team in teams:
            _d[team.id] = {
                'message': team.name,
                'prefix': 'team-u'
            }

    await callback.message.edit_text(f"Ваши подписки на {sub_name}:",
                     reply_markup=enum_call_kb(_d, page=0, kb_on_page=6, call_back_back='profile'))

@dp.message(Command('logs'))
async def send_logs(message: types.Message):
    logger.info(f"send_logs called by {message.from_user.id}")
    if db_manager.check_user_is_admin(message.from_user.id):
        file = types.FSInputFile(r'logs/logs.log')
        await message.answer_document(document=file)

@dp.message(Command('db'))
async def send_db(message: types.Message):
    logger.info(f"send_db called by {message.from_user.id}")
    if db_manager.check_user_is_admin(message.from_user.id):
        file = types.FSInputFile(r'data/app.db')
        await message.answer_document(document=file)

async def mailing():
    logger.info(f"start mailing")
    matches = db_manager.get_ongoing_matches()
    for match in matches:
        if match.notified:
            continue
        users = db_manager.get_users_subscribed_to_match(match.url)
        message = f"Турнир: {match.event.name}\nКоманды: {' - '.join([team.name for team in match.teams])}\nФормат: {match.format}\nСтраница на HLTV: {match.url}"
        for user in users:
            streams = db_manager.get_streams_for_match(match.url)
            stream_d = {}
            for stream in streams:
                stream_d[stream.name] = stream.link
            await bot.send_message(user.id, message, reply_markup=enum_links_kb(stream_d))
        db_manager.set_notifed_match(match.url)