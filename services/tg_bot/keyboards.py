from aiogram import types
import values
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

from values import but_equipment_filter, but_capacity_aud


def create_start_keyboard() -> ReplyKeyboardMarkup:
    keyboard_buttons = [[KeyboardButton(text=values.but_watch_schedule), KeyboardButton(text=values.but_filter_cab)]]
    keyboard = ReplyKeyboardMarkup(keyboard=keyboard_buttons, resize_keyboard=True)
    return keyboard



def create_inline_keyboard_diff_len(count: int) -> InlineKeyboardMarkup:
    # count = количество похожих аудиторий в бд
    keyboard_buttons = []
    row = []
    for i in range(1, count + 1):
        button_text = f"№ {i}"
        callback_data = f"audience:{i}"
        button = InlineKeyboardButton(text=button_text, callback_data=callback_data)
        row.append(button)

        if len(row) == 3:
            keyboard_buttons.append(row)
            row = []

    if row:
        keyboard_buttons.append(row)

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    return keyboard


def create_inline_filtered_keyboard() -> InlineKeyboardMarkup:
    keyboard_button = []
    row = []
    row.append(InlineKeyboardButton(text=but_equipment_filter, callback_data=f"filter_equipment"))
    row.append(InlineKeyboardButton(text=but_capacity_aud, callback_data=f"filter_capacity"))
    keyboard_button.append(row)
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_button)
    return keyboard