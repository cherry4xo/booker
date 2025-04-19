import asyncio
import random
import uuid
from datetime import datetime, time, timedelta, date

from faker import Faker # Библиотека для генерации фейковых данных
from tortoise import Tortoise, run_async
from tortoise.exceptions import IntegrityError
from tortoise.query_utils import Prefetch

# --- Настройки ---
# Укажи правильные пути импорта относительно места запуска скрипта
try:
    from app.models import User, Equipment, Auditorium, AvailabilitySlot, Booking
    from app.enums import UserRole
    from app.db import TORTOISE_ORM # Импортируй настройки Tortoise
    from app.utils import password # Импортируй твой хелпер для хеширования паролей
except ImportError as e:
    print(f"Ошибка импорта: {e}")
    print("Убедись, что скрипт запускается из правильной директории или настроены пути PYTHONPATH.")
    exit(1)

# --- Константы (настрой по желанию) ---
NUM_USERS = 20
NUM_MODERATORS = 3
NUM_EQUIPMENT = 10
NUM_AUDITORIUMS = 15
NUM_AVAILABILITY_PER_AUDITORIUM = 2 # Например, будни и выходные
NUM_BOOKINGS_PER_AUDITORIUM = 30 # Количество броней на аудиторию
BOOKING_DATE_RANGE_DAYS = 60 # Диапазон дат для бронирований (+/- от сегодня)

# Создаем экземпляр Faker
fake = Faker('ru_RU') # Используем русскую локализацию для имен

async def seed_users():
    """Создает тестовых пользователей и модераторов."""
    print("Создание пользователей...")
    users = []
    # Создаем обычных пользователей
    for i in range(NUM_USERS):
        username = fake.user_name() + str(i) # Добавляем число для уникальности
        email = f"{username}@example.com"
        raw_password = "password123" # Используй одинаковый пароль для простоты

        try:
            user = User(
                uuid=uuid.uuid4(),
                username=username,
                email=email,
                password_hash=password.get_password_hash(raw_password), # Хешируем пароль
                role=UserRole.BOOKER,
                registration_date=fake.date_this_decade()
            )
            await user.save()
            users.append(user)
            print(f"  Пользователь создан: {username} ({email})")
        except IntegrityError:
            print(f"  Пользователь {username} или email {email} уже существует, пропуск.")
            # Можно попытаться получить существующего пользователя, если нужно
            existing_user = await User.get_or_none(username=username) or await User.get_or_none(email=email)
            if existing_user:
                users.append(existing_user)

    # Создаем модераторов
    for i in range(NUM_MODERATORS):
        username = f"moderator_{i}"
        email = f"{username}@example.com"
        raw_password = "password123"
        try:
            mod = User(
                uuid=uuid.uuid4(),
                username=username,
                email=email,
                password_hash=password.get_password_hash(raw_password),
                role=UserRole.MODERATOR, # Устанавливаем роль модератора
                registration_date=fake.date_this_decade()
            )
            await mod.save()
            users.append(mod)
            print(f"  Модератор создан: {username} ({email})")
        except IntegrityError:
            print(f"  Модератор {username} или email {email} уже существует, пропуск.")
            existing_user = await User.get_or_none(username=username) or await User.get_or_none(email=email)
            if existing_user:
                users.append(existing_user)

    print(f"Всего создано/найдено пользователей: {len(users)}")
    return users

async def seed_equipment():
    """Создает тестовое оборудование."""
    print("Создание оборудования...")
    equipment_list = []
    equipment_names = [
        "Проектор", "Экран", "Маркерная доска", "Флип-чарт", "Компьютер",
        "Колонки", "Микрофон", "Веб-камера", "Кондиционер", "Столы", "Стулья"
    ]
    # Ограничим количество создаваемого оборудования, чтобы избежать дубликатов имен
    num_to_create = min(NUM_EQUIPMENT, len(equipment_names))

    for i in range(num_to_create):
        name = equipment_names[i]
        description = fake.sentence(nb_words=10)
        try:
            # Модель Equipment.create не существует в предоставленном коде, используем new/save
            # eq = await Equipment.create(name=name, description=description) # Если бы был метод create
            eq = Equipment(
                uuid=uuid.uuid4(),
                name=name,
                description=description
            )
            await eq.save()
            equipment_list.append(eq)
            print(f"  Оборудование создано: {name}")
        except IntegrityError:
            print(f"  Оборудование '{name}' уже существует, пропуск.")
            existing_eq = await Equipment.get_or_none(name=name)
            if existing_eq:
                 equipment_list.append(existing_eq)

    print(f"Всего создано/найдено оборудования: {len(equipment_list)}")
    return equipment_list

async def seed_auditoriums(equipment_list):
    """Создает тестовые аудитории и связывает их с оборудованием."""
    print("Создание аудиторий...")
    if not equipment_list:
        print("  Нет доступного оборудования для добавления в аудитории.")

    auditoriums = []
    for i in range(NUM_AUDITORIUMS):
        identifier = f"Ауд. {fake.random_int(min=101, max=999)}-{fake.random_element(elements=('К', 'Л', 'М'))}"
        capacity = fake.random_int(min=10, max=100)
        description = f"Учебная аудитория {identifier}. {fake.sentence(nb_words=8)}"

        try:
            # Сначала создаем и сохраняем аудиторию
            aud = Auditorium(
                uuid=uuid.uuid4(),
                identifier=identifier,
                capacity=capacity,
                description=description # Исправлено с desctiption на description
            )
            await aud.save()
            print(f"  Аудитория создана: {identifier} (вместимость: {capacity})")

            # Затем добавляем случайное оборудование (если оно есть)
            if equipment_list:
                # Выбираем случайное количество оборудования (от 0 до 5, но не больше чем есть)
                num_eq_to_add = random.randint(0, min(5, len(equipment_list)))
                selected_equipment = random.sample(equipment_list, num_eq_to_add)
                if selected_equipment:
                    await aud.equipment.add(*selected_equipment) # Добавляем оборудование через M2M
                    eq_names = ", ".join([eq.name for eq in selected_equipment])
                    print(f"    -> Добавлено оборудование: {eq_names}")

            auditoriums.append(aud)
        except IntegrityError:
            print(f"  Аудитория с идентификатором '{identifier}' уже существует, пропуск.")
            existing_aud = await Auditorium.get_or_none(identifier=identifier)
            if existing_aud:
                 auditoriums.append(existing_aud)

    print(f"Всего создано/найдено аудиторий: {len(auditoriums)}")
    return auditoriums

async def seed_availability(auditoriums):
    """Создает слоты доступности для аудиторий."""
    print("Создание слотов доступности...")
    if not auditoriums:
        print("  Нет аудиторий для создания слотов доступности.")
        return

    for aud in auditoriums:
        print(f"  Для аудитории: {aud.identifier}")
        # Пример: Доступность Пн-Пт с 9:00 до 18:00
        for day in range(5): # 0=Пн, 4=Пт
            start_time = time(9, 0)
            end_time = time(18, 0)
            try:
                # Используем прямое создание модели, т.к. create в модели ожидает схему
                slot = AvailabilitySlot(
                    uuid=uuid.uuid4(),
                    auditorium=aud,
                    day_of_week=day,
                    start_time=start_time,
                    end_time=end_time
                )
                await slot.save()
                print(f"    -> Добавлен слот: {day} ({start_time}-{end_time})")
            except IntegrityError as e: # Ловим и другие возможные конфликты unique_together
                 print(f"    -> Ошибка создания слота для дня {day}: {e}, пропуск.")

        # Можно добавить и другие слоты, например, для субботы с другим временем

async def seed_bookings(users, auditoriums):
    """Создает тестовые бронирования."""
    print("Создание бронирований...")
    if not users or not auditoriums:
        print("  Нет пользователей или аудиторий для создания бронирований.")
        return

    bookers = [u for u in users if u.role == UserRole.BOOKER]
    if not bookers:
        print("  Нет пользователей с ролью 'booker' для создания бронирований.")
        return

    today = date.today()
    total_bookings_created = 0

    for aud in auditoriums:
        print(f"  Для аудитории: {aud.identifier}")

        availability_slots = await AvailabilitySlot.filter(auditorium_id=aud.uuid).all()

        if not availability_slots:
            print("    -> Нет слотов доступности, бронирования не могут быть созданы.")
            continue

        # now slots_by_day will work as you'd expect:
        slots_by_day = {day: [] for day in range(7)}
        for slot in availability_slots:
            slots_by_day[slot.day_of_week].append(slot)

        bookings_created_for_aud = 0
        attempts = 0 # Предотвращение бесконечного цикла, если не удается найти слот

        while bookings_created_for_aud < NUM_BOOKINGS_PER_AUDITORIUM and attempts < NUM_BOOKINGS_PER_AUDITORIUM * 5:
            attempts += 1
            # Выбираем случайного пользователя
            booker = random.choice(bookers)
            # Выбираем случайную дату в диапазоне
            booking_date = today + timedelta(days=random.randint(-BOOKING_DATE_RANGE_DAYS // 2, BOOKING_DATE_RANGE_DAYS // 2))
            day_of_week = booking_date.weekday()

            # Находим подходящие слоты на этот день недели
            possible_slots = slots_by_day.get(day_of_week, [])
            if not possible_slots:
                continue # Нет доступности в этот день недели

            # Выбираем случайный слот из доступных на этот день
            chosen_slot = random.choice(possible_slots)

            # Генерируем время начала внутри слота
            slot_start_dt = datetime.combine(booking_date, chosen_slot.start_time)
            # Корректно обрабатываем end_time 00:00 как конец дня
            slot_end_time = chosen_slot.end_time if chosen_slot.end_time != time(0, 0) else time(23, 59, 59)
            slot_end_dt = datetime.combine(booking_date, slot_end_time)

            if slot_start_dt >= slot_end_dt: continue # Пропускаем некорректные слоты

            # Генерируем случайное время начала (с шагом 15 мин)
            possible_starts = []
            current_dt = slot_start_dt
            while current_dt < slot_end_dt:
                 possible_starts.append(current_dt)
                 current_dt += timedelta(minutes=15) # Бронируем с шагом 15 минут

            if not possible_starts: continue

            start_time = random.choice(possible_starts)

            # Генерируем случайную длительность (1-3 часа с шагом 30 мин)
            duration_hours = random.choice([1, 1.5, 2, 2.5, 3])
            end_time = start_time + timedelta(hours=duration_hours)

            # Проверяем, что время окончания не выходит за пределы слота доступности
            if end_time > slot_end_dt:
                continue # Время бронирования выходит за рамки доступности

            # Проверяем наложение с уже существующими бронями (упрощенная проверка)
            # (BookingStart < QueryEnd) AND (BookingEnd > QueryStart)
            # overlapping = await Booking.filter(
            #     auditorium_id=aud.uuid,
            #     start_time__lt=end_time,
            #     end_time__gt=start_time
            # ).exists()

            # if overlapping:
            #     # print(f"    -> Конфликт времени для {start_time} - {end_time}, попытка снова.")
            #     continue # Конфликт, пробуем сгенерировать другое время

            # Создаем бронирование
            try:
                booking = Booking(
                    uuid=uuid.uuid4(),
                    broker=booker,
                    auditorium=aud,
                    start_time=start_time,
                    end_time=end_time,
                    title=f"Мероприятие {fake.word()} {random.randint(1,100)}"
                )
                await booking.save()
                print(f"    -> Создано бронирование: {start_time.strftime('%Y-%m-%d %H:%M')} - {end_time.strftime('%H:%M')} ({booker.username})")
                bookings_created_for_aud += 1
                total_bookings_created += 1
            except IntegrityError as e: # На случай других конфликтов
                 print(f"    -> Ошибка IntegrityError при создании бронирования: {e}")
            except Exception as e:
                 print(f"    -> Непредвиденная ошибка при создании бронирования: {e}")

        if attempts >= NUM_BOOKINGS_PER_AUDITORIUM * 5:
             print(f"    -> Достигнут лимит попыток создания бронирований для {aud.identifier}.")

    print(f"Всего создано бронирований: {total_bookings_created}")


async def run_seeding():
    """Основная функция для запуска сидинга."""
    print("Инициализация Tortoise ORM...")
    try:
        await Tortoise.init(config=TORTOISE_ORM)
        print("Соединение с БД установлено.")
        print("Генерация схем (если таблицы не существуют)...")
        await Tortoise.generate_schemas() # Создаст таблицы, если их нет
        print("Схемы сгенерированы.")

        # Запуск сидинга в правильном порядке зависимостей
        created_users = await seed_users()
        created_equipment = await seed_equipment()
        created_auditoriums = await seed_auditoriums(created_equipment)
        await seed_availability(created_auditoriums)
        await seed_bookings(created_users, created_auditoriums)

        print("\nСидинг базы данных успешно завершен!")

    except Exception as e:
        print(f"\nПроизошла ошибка во время сидинга: {e}")
    finally:
        print("Закрытие соединения с БД...")
        await Tortoise.close_connections()
        print("Соединение закрыто.")

if __name__ == "__main__":
    print("Запуск скрипта сидинга базы данных...")
    # Используем asyncio.run() для запуска асинхронной функции run_seeding()
    # В Python 3.7+
    asyncio.run(run_seeding())
    # Для более старых версий Python:
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(run_seeding())