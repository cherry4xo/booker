import math
from typing import List

from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder

import values
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

from values import but_equipment_filter, but_capacity_aud


def create_start_keyboard() -> ReplyKeyboardMarkup:
    keyboard_buttons = [[KeyboardButton(text=values.but_watch_schedule), KeyboardButton(text=values.but_filter_cab)]]
    keyboard = ReplyKeyboardMarkup(keyboard=keyboard_buttons, resize_keyboard=True)
    return keyboard



# def create_inline_keyboard_diff_len(count: int) -> InlineKeyboardMarkup:
#     # count = количество похожих аудиторий в бд
#     keyboard_buttons = []
#     row = []
#     for i in range(1, count + 1):
#         button_text = f"№ {i}"
#         callback_data = f"audience:{i}"
#         button = InlineKeyboardButton(text=button_text, callback_data=callback_data)
#         row.append(button)
#
#         if len(row) == 5:
#             keyboard_buttons.append(row)
#             row = []
#
#     if row:
#         keyboard_buttons.append(row)
#
#     keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
#     return keyboard


def create_keyboard(page_num, aud_names):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    total_pages = (len(aud_names) + 9 - 1) // 9

    start_index = page_num * 9
    end_index = min((page_num + 1) * 9, len(aud_names))

    row = []
    for i in range(start_index, end_index):
        item = str(aud_names[i])
        button = InlineKeyboardButton(text=item, callback_data=f"item_{item}")
        row.append(button)
        if len(row) == 3:
            keyboard.inline_keyboard.append(row)
            row = []
    if row:
        keyboard.inline_keyboard.append(row)

    nav_row = []
    if page_num > 0:
        nav_row.append(InlineKeyboardButton(text="<-", callback_data=f"page_{page_num - 1}"))

    nav_row.append(InlineKeyboardButton(text=f"{page_num + 1}/{total_pages}", callback_data="current_page"))

    if page_num < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text="->", callback_data=f"page_{page_num + 1}"))

    keyboard.inline_keyboard.append(nav_row)

    return keyboard




def create_inline_filtered_keyboard() -> InlineKeyboardMarkup:
    keyboard_button = []
    row = []
    row.append(InlineKeyboardButton(text=but_equipment_filter, callback_data=f"filter_equipment"))
    row.append(InlineKeyboardButton(text=but_capacity_aud, callback_data=f"filter_capacity"))
    keyboard_button.append(row)
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_button)
    return keyboard