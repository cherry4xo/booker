from os import getenv
from  dotenv import load_dotenv

import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message
import keyboards
import values
import app.db

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
app2 = FastApi()
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
    #TODO просмотр расписания всех аудиторий
    await state.set_state(watch_cab.input_cab)


@dp.message(watch_cab.input_cab)
async def watch_schedule_print_all_cab(message: Message, state: FSMContext):
    aud_num = message.text
    await message.answer(f'all auditories\n')
    all_aud = await get_auditoriums()
    if all_aud:
        for x in all_aud:
            await message.answer(f"{x}")

    # schedule_items = get_auditoriums()
    # await message.answer(f'{schedule_items}')
    #
    # schedule_items = await models.Auditorium.filter(identifier__icontains=aud_num).all()
    #
    # if not schedule_items:
    #     await message.answer(f"No schedules found containing '{aud_num}'.")
    #     await state.clear()
    #     return

    await message.answer(f"ITEM FOUND!!!")
    # schedule_text = f"Schedules containing '{aud_num}':\n"
    # count_audience = len(schedule_text)
    # for item in schedule_items:
    #     schedule_text += f"- {item.date}: {item.time}: {item.subject} (Room: {item.classroom_number})\n"
    #
    # await message.answer(schedule_text)
    # await state.update_data(aud_num)
    await state.set_state(watch_cab.print_same_cab)
    await process_callback(message, state, 2)

async def process_callback(message: Message, state: FSMContext, len: int = 2):
    #TODO запрос к бд и поиск похожих аудиторий, после которого формируется Inline клавиатура
    list_cab = keyboards.create_inline_keyboard_diff_len(len)
    await message.answer(f'В данный момент доступно {len} аудиторий, выберите нужную',  reply_markup=list_cab)
    await state.set_state(watch_cab.input_certain_cab)

@dp.callback_query(F.data.startswith('audience:'), watch_cab.input_certain_cab)
async def certain_aud(callback_query: types.CallbackQuery, state: FSMContext):
    data = callback_query.data.split(":")
    audience_number = data[1]
    await callback_query.message.answer(text=f"Вы выбрали аудиторию {audience_number}",
                                        reply_markup=keyboards.create_start_keyboard())
    res_data = await state.get_data()
    #TODO вытащить расписание из БД именно этой аудитории
    await state.clear()

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


@dp.message(filter_cab_state.print_filtered_cab_capacity)
async def print_filtered_cab_capacity(message: Message, state: FSMContext):
    capacity = int(message.text)

    auditoriums = await models.Auditorium.filter(capacity=capacity).all()
    if auditoriums:
        response = f"Аудитории с вместимостью {capacity}:\n"
        for auditorium in auditoriums:
            response += f"- {auditorium.identifier} (UUID: {auditorium.uuid})\n"
        await message.answer(response)
    else:
        await message.answer(f"Аудитории с вместимостью {capacity} не найдены.")
    await state.clear()




@dp.callback_query(F.data.startswith("filter_equipment"))
async def chosen_equipment(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.answer(f"Введите оборудование по которому хотите отфильтровать!")
    await state.set_state(filter_cab_state.print_filtered_cab_equip)

@dp.message(filter_cab_state.print_filtered_cab_equip)
async def input_filter_cab(message: Message, state: FSMContext):
    filter = 'ноутбук'
    await message.answer(f'Entry func')
    equip_id = await models.Equipment.get_by_name(filter)
    await message.answer(f'your equip = {filter}, equip_id = {equip_id}')


    # await state.update_data(filter)
    # filtered_cab = await models.Equipment.get_by_name(filter)
    #
    # if not filtered_cab:
    #     await message.answer(f"No schedules found containing '{filter}'.")
    #     await state.clear()
    #     return
    # else:
    #     message.answer(f"ITEM FOUND!!!")
    # schedule_text = f"Schedules containing '{filter}':\n"
    # for item in filtered_cab:
    #     schedule_text += f"- {item.date}: {item.time}: {item.subject} (Room: {item.classroom_number})\n"
    #
    # await message.answer(schedule_text)
    # await state.clear()

""" Button Просмотр по фильтрам"""


async def main():
    await db.init(app)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())