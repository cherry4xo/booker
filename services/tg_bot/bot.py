from ftplib import all_errors
from os import getenv
from typing import List

from  dotenv import load_dotenv

import asyncio
import logging
from fastapi import FastAPI
from aiogram import Bot, Dispatcher, types, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message
from pyexpat.errors import messages

import keyboards
import values
# import app.db
from app.services import auditorium
from app import db
from app import models

"""
наблюдатель в боте
просмотр актуального расписания
просмотр аудиторий под характеристики

клавиатура которая внизу (получения расписание аудитории, 
вводишь с клавиутары номер и выводить похожие
фильтрация по количеству мест)

"""



load_dotenv()
Token  = getenv("TOKEN")
bot = Bot(token=str(Token), default=DefaultBotProperties(parse_mode=ParseMode.HTML))
app = FastAPI()
dp = Dispatcher()

@dp.message(CommandStart())
async def command_start_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(f"Привет {message.from_user.full_name}!\n"
                         f"Добро пожаловать в нашего бота бронирования аудиторий",
                         reply_markup=keyboards.create_start_keyboard().one_time_keyboard,
                         parse_mode=ParseMode.HTML)

""" Button Просмотр расписания определенной аудитории"""
class watch_cab(StatesGroup):
    input_cab = State() # Ввод изначальной "сырой" аудитории
    print_same_cab = State() # Вывод похожих на сырую аудиторию
    input_certain_cab = State() # Выбор по кнопке определенной правильной аудитории

@dp.message(F.text == values.but_watch_schedule)
async def watch_schedule(message: Message, state: FSMContext):
    await message.answer(f"Введите номер аудитории который хотите посмотреть\n")
    await state.set_state(watch_cab.input_cab)

class StateInline(StatesGroup):
    waiting_for_items = State()

@dp.message(watch_cab.input_cab)
async def watch_schedule_print_all_cab(message: Message, state: FSMContext):
    aud_num = message.text
    auditoriums = await models.Auditorium.filter(identifier__icontains=aud_num)
    aud_names = [aud.identifier for aud in auditoriums]
    await state.update_data(all_items=aud_names)
    await process_callback(message, aud_names)
    await state.set_state(watch_cab.print_same_cab)

async def process_callback(message: Message, aud_names: List):
    list_cab = keyboards.create_keyboard(0, aud_names)
    await message.answer(f'В данный момент доступно {len(aud_names)} аудиторий, выберите нужную',  reply_markup=list_cab,
                         parse_mode=ParseMode.HTML)


@dp.callback_query(F.data.startswith('page_'))
async def page_callback_handler(query: types.CallbackQuery, state: FSMContext ):
    page_num = int(query.data.split('_')[1])
    data = await state.get_data()
    aud_names = data.get("all_items")
    keyboard = keyboards.create_keyboard(page_num, aud_names)
    content = f'В данный момент доступно {len(aud_names)} аудиторий, выберите нужную'
    await query.message.edit_text(text=content, reply_markup=keyboard)
    await query.answer()


async def get_availability_slots_for_auditorium(identifier: str):
    try:
        auditorium = await models.Auditorium.get(identifier=identifier)
        # 2. Получаем все связанные слоты доступности
        availability_slots = await models.AvailabilitySlot.filter(auditorium=auditorium).order_by("day_of_week", "start_time")
        return availability_slots
    except Exception as e:
        print(f"Ошибка при получении слотов: {e}")
        return []

@dp.callback_query(F.data.startswith('item_'))
async def certain_aud(callback_query: types.CallbackQuery, state: FSMContext):
    data = callback_query.data.split("_")
    audience_number = data[1]
    await callback_query.message.answer(text=f"Вы выбрали {audience_number}",
                                        reply_markup=keyboards.create_start_keyboard())
    res_aud = await models.Auditorium.get_by_name(audience_number)
    aud_time = await get_availability_slots_for_auditorium(res_aud.identifier)
    text = []
    for slot in aud_time:
        # text.append(models.AvailabilitySlot.format_availability_slot(slot.__str__()))
        text.append(slot.__str__())
    await state.update_data(all_items=text)
    await callback_query.message.answer(f'{text}', parse_mode=ParseMode.HTML)
    await state.clear()
    await callback_query.answer()




""" Button Просмотр расписания определенной аудитории"""



""" Button Просмотр по фильтрам"""
class filter_cab_state(StatesGroup):
    choose_filter = State()
    print_filtered_cab_equip = State()
    print_filtered_cab_capacity = State()


@dp.message(F.text == values.but_filter_cab)
async def filter_cab(message: Message, state: FSMContext):
    await state.set_state(filter_cab_state.choose_filter)
    await message.answer(f"Выберите фильтр для сортировки!\n",
                         reply_markup=keyboards.create_inline_filtered_keyboard())

@dp.callback_query(F.data.startswith("filter_capacity"))
async def chosen_capacity(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.answer(f"Введите количество мест в аудитории")
    await state.set_state(filter_cab_state.print_filtered_cab_capacity)
    await callback_query.answer()


@dp.message(filter_cab_state.print_filtered_cab_capacity)
async def print_filtered_cab_capacity(message: Message, state: FSMContext):
    capacity = int(message.text)

    auditoriums = await models.Auditorium.filter(capacity=capacity).all()
    aud_names = [aud.identifier for aud in auditoriums]
    await state.update_data(all_items=aud_names)
    if auditoriums:
        await process_callback(message,  aud_names)
    else:
        await message.answer(f"Аудитории с вместимостью {capacity} не найдены.")




@dp.callback_query(F.data.startswith("filter_equipment"))
async def chosen_equipment(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.answer(f"Введите оборудование по которому хотите отфильтровать!")
    await state.set_state(filter_cab_state.print_filtered_cab_equip)

@dp.message(filter_cab_state.print_filtered_cab_equip)
async def input_filter_cab(message: Message, state: FSMContext):
    filter = message.text
    equipment = await models.Equipment.get_by_name(filter)
    auditoriums = await models.Auditorium.filter(equipment=equipment).all()
    aud_names = [aud.identifier for aud in auditoriums]
    await state.update_data(all_items=aud_names)
    await process_callback(message, aud_names)

""" Button Просмотр по фильтрам"""


async def main():
    await db.init(app)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())