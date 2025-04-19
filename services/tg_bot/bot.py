from os import getenv
from  dotenv import load_dotenv

import asyncio
import logging
from aiogram import Bot, Dispatcher, types, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message
import  keyboards
import values
from app.models import Auditorium

"""
наблюдатель в боте
просмотр актуального расписания
просмотр аудиторий под характеристики


клавиатура которая внизу (получения расписание аудитории, 
вводишь с клавиутары номер и выводить похожие
фильтрация по количеству мест)

"""



load_dotenv()
# Token  = getenv("TOKEN")
Token = "7904999198:AAHdIlCXSBE9D_KfBecbGVbeU2imF2Pq12E"
bot = Bot(token=Token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

@dp.message(CommandStart())
async def command_start_handler(message: Message):
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
    #TODO просмотр расписания всех аудиторий
    await state.set_state(watch_cab.input_cab)


@dp.message(watch_cab.input_cab)
async def watch_schedule_print_all_cab(message: Message, state: FSMContext):
    aud_num = message.text
    schedule_items = await Auditorium.filter(subject__icontains=aud_num).all()

    if not schedule_items:
        await message.answer(f"No schedules found containing '{aud_num}'.")
        await state.clear()
        return

    schedule_text = f"Schedules containing '{aud_num}':\n"
    for item in schedule_items:
        # Adjust the formatting based on your model's fields
        schedule_text += f"- {item.date}: {item.time}: {item.subject} (Room: {item.classroom_number})\n"

    await message.answer(schedule_text)
    await state.clear()
    await state.update_data(aud_num)
    await state.set_state(watch_cab.print_same_cab)
    await process_callback(message, state)

async def process_callback(message: Message, state: FSMContext):
    #TODO запрос к бд и поиск похожих аудиторий, после которого формируется Inline клавиатура
    list_cab = keyboards.create_inline_keyboard_diff_len(5, message.chat.id)
    await message.answer(f'В данный момент доступно 5 аудиторий, выберите нужную',  reply_markup=list_cab)
    await state.set_state(watch_cab.input_certain_cab)

@dp.callback_query(F.data.startswith('audience:'), watch_cab.input_certain_cab)
async def certain_aud(callback_query: types.CallbackQuery, state: FSMContext):
    data = callback_query.data.split(":")
    audience_number = data[1]
    await callback_query.message.answer(text=f"Вы выбрали аудиторию {audience_number}",
                                        reply_markup=keyboards.create_start_keyboard())
    res_data = await state.get_data()
    await state.clear()

""" Button Просмотр расписания определенной аудитории"""



""" Button Просмотр по фильтрам"""
class filter_cab(StatesGroup):
    input_cab = State() # Ввод изначальной "сырой" аудитории
    print_same_cab = State() # Вывод похожих на сырую аудиторию
    input_certain_cab = State() # Выбор по кнопке определенной правильной аудитории


@dp.message(F.text == values.but_filter_cab)
async def filter_cab(message: Message):
    await message.answer(f"Аудитории не добавлены!\n")

""" Button Просмотр по фильтрам"""


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())