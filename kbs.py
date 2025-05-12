from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from math import ceil

def back_kb(call_back):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text='Назад',
            callback_data=call_back
        )
    )
    builder.adjust(1)
    return builder.as_markup()

def sub_kb(call_back_sub: str, call_back_back: str):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text='Подписаться' if call_back_sub[:2] == 'su' else 'Отписаться',
            callback_data=call_back_sub
        ),

        InlineKeyboardButton(
            text='Назад',
            callback_data=call_back_back
        )
    )
    builder.adjust(1)
    return builder.as_markup()

def basic_kb():
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(text="Все турниры", callback_data='all_events'))
    builder.row(InlineKeyboardButton(text="Все команды", callback_data='all_teams'))
    builder.row(InlineKeyboardButton(text="Ближайшие события", callback_data='my_matches'))
    builder.row(InlineKeyboardButton(text="Профиль", callback_data='profile'))

    builder.adjust(1)
    return builder.as_markup()

def enum_call_kb(data: dict, page, kb_on_page, call_back_back='base'):
    show_mode = 0
    builder = InlineKeyboardBuilder()
    print_data = list(data.keys())[page * kb_on_page:]
    if len(print_data) > kb_on_page:
        print_data = print_data[:kb_on_page]
    else:
        show_mode = 1
    if not page: show_mode = -1
    if len(data) <= kb_on_page: show_mode = 2

    for id in print_data:
        builder.row(
            InlineKeyboardButton(
                text=data[id]['message'],
                callback_data=f"data_{data[id]['prefix']}_{id}"
            )
        )

    if not show_mode:
        builder.row(
            InlineKeyboardButton(
                text='<',
                callback_data=f"_{data[print_data[0]]['prefix']}_back_{page}"
            ),
            InlineKeyboardButton(
                text=f'{page + 1}/{ceil(len(data) / kb_on_page)}',
                callback_data='.'
            ),
            InlineKeyboardButton(
                text='>',
                callback_data=f"_{data[print_data[0]]['prefix']}_forward_{page}"
            )
        )
    elif show_mode == 1:
        builder.row(
            InlineKeyboardButton(
                text='<',
                callback_data=f"_{data[print_data[0]]['prefix']}_back_{page}"
            ),
            InlineKeyboardButton(
                text=f'{page + 1}/{ceil(len(data) / kb_on_page)}',
                callback_data='.'
            ),
            InlineKeyboardButton(
                text=f'...',
                callback_data='.'
            )
        )
    elif show_mode == 2:
        builder.row(
            InlineKeyboardButton(
                text='...',
                callback_data='.'
            ),
            InlineKeyboardButton(
                text=f'{page + 1}/{ceil(len(data) / kb_on_page)}',
                callback_data='.'
            ),
            InlineKeyboardButton(
                text=f'...',
                callback_data='.'
            )
        )
    else:
        builder.row(
            InlineKeyboardButton(
                text=f'...',
                callback_data='.'
            ),
            InlineKeyboardButton(
                text=f'{page + 1}/{ceil(len(data) / kb_on_page)}',
                callback_data='.'
            ),
            InlineKeyboardButton(
                text='>',
                callback_data=f"_{data[print_data[0]]['prefix']}_forward_{page}"
            )
        )

    builder.row(
        InlineKeyboardButton(
            text='Назад',
            callback_data=call_back_back
        )
    )

    return builder.as_markup()

def subscribe_kb():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text='Турниры',
            callback_data='show_sub_events'
        ),
        InlineKeyboardButton(
            text='Команды',
            callback_data='show_sub_teams'
        ),
        InlineKeyboardButton(
            text='Назад',
            callback_data='base'
        )
    )
    builder.adjust(1)
    return builder.as_markup()

def enum_links_kb(data: dict):
    builder = InlineKeyboardBuilder()
    for text in data.keys():
        builder.row(
            InlineKeyboardButton(
                text=text,
                url=data[text]
            )
        )

    builder.adjust(1)
    return builder.as_markup()