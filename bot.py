import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import StatesGroup, State
from config import BOT_TOKEN
from models import SessionLocal, User, ScheduleSlot, Booking
from sqlalchemy import select, and_
import re
import datetime
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
import logging
from sqlalchemy import String

ADMIN_IDS = [823862864]  # Telegram ID администратора

dp = Dispatcher(storage=MemoryStorage())
bot = Bot(token=str(BOT_TOKEN))

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

@dp.errors()
async def error_handler(update, exception):
    logging.error(f"Ошибка: {exception} при обработке {update}")
    return True

class BookingStates(StatesGroup):
    entering_name = State()
    choosing_date = State()
    choosing_time = State()
    entering_phone = State()
    confirming = State()

class AdminDeleteStates(StatesGroup):
    choosing_date = State()
    choosing_time = State()
    confirming = State()

class AdminAddSlotStates(StatesGroup):
    choosing_date = State()
    entering_times = State()
    confirming = State()

START_TEXT = (
    "👋 Добро пожаловать!\n\n"
    "Этот чат-бот предназначен для записи на ресницы к мастеру Пушкаревой Виктории в г. Глазове.\n\n"
    "Выберите снизу \"Записаться\", затем удобную дату и время.\n\n"
    "Также вы можете посмотреть свои записи или связаться с мастером."
)

MAIN_MENU_KB = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Записаться")],
        [KeyboardButton(text="Мои записи")],
        [KeyboardButton(text="Свободные слоты")],
    ], resize_keyboard=True
)

ADMIN_MENU_KB = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Записаться")],
        [KeyboardButton(text="Мои записи")],
        [KeyboardButton(text="Свободные слоты")],
        [KeyboardButton(text="Админ-панель")],
    ], resize_keyboard=True
)

BACK_KB = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="/start")]],
    resize_keyboard=True
)

def get_dates_keyboard():
    today = datetime.date.today()
    dates = [today + datetime.timedelta(days=i) for i in range(7)]
    row = []
    kb = []
    for i, d in enumerate(dates):
        row.append(KeyboardButton(text=d.strftime('%Y-%m-%d')))
        if (i + 1) % 3 == 0 or i == len(dates) - 1:
            kb.append(row)
            row = []
    kb.append([KeyboardButton(text="/start")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

@dp.message(Command('start'))
async def cmd_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id if message.from_user and message.from_user.id else None
    if not user_id:
        await message.answer("Ошибка: не удалось определить ваш Telegram ID.")
        return
    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.telegram_id == user_id))
        if not user:
            user = User(telegram_id=user_id, phone="", is_admin=user_id in ADMIN_IDS)
            session.add(user)
            await session.commit()
        if user.is_admin:
            await message.answer(START_TEXT, reply_markup=ADMIN_MENU_KB)
        else:
            await message.answer(START_TEXT, reply_markup=MAIN_MENU_KB)
    await state.clear()

@dp.message(lambda m: m.text == "Записаться")
async def ru_book(message: types.Message, state: FSMContext):
    await start_booking(message, state)

@dp.message(lambda m: m.text == "Мои записи")
async def ru_my_bookings(message: types.Message):
    await my_bookings(message)

@dp.message(Command('Мои записи'))
async def my_bookings_ru(message: types.Message):
    await my_bookings(message)

@dp.message(lambda m: m.text == "Админ-панель")
async def ru_admin_panel(message: types.Message):
    await admin_panel(message)

@dp.message(Command('book'))
async def start_booking(message: types.Message, state: FSMContext):
    await state.set_state(BookingStates.entering_name)
    await message.answer("Пожалуйста, введите ваше имя:", reply_markup=types.ReplyKeyboardRemove())

@dp.message(BookingStates.entering_name)
async def enter_name(message: types.Message, state: FSMContext):
    if message.text == "/start":
        await cmd_start(message, state)
        return
    if not message.text or len(message.text.strip()) < 2:
        await message.answer("Пожалуйста, введите корректное имя (минимум 2 буквы).", reply_markup=BACK_KB)
        return
    await state.update_data(name=message.text.strip())
    await state.set_state(BookingStates.choosing_date)
    await message.answer("Выберите дату:", reply_markup=get_dates_keyboard())

@dp.message(BookingStates.choosing_date)
async def choose_date(message: types.Message, state: FSMContext):
    if message.text == "/start":
        await cmd_start(message, state)
        return
    if not message.text:
        await message.answer("Пожалуйста, выберите дату из списка.", reply_markup=get_dates_keyboard())
        return
    try:
        date = datetime.datetime.strptime(message.text, '%Y-%m-%d').date()
    except ValueError:
        await message.answer("Пожалуйста, выберите дату из списка.", reply_markup=get_dates_keyboard())
        return
    await state.update_data(date=date)
    # Получаем только свободные слоты времени
    async with SessionLocal() as session:
        slots = await session.scalars(select(ScheduleSlot).where(and_(ScheduleSlot.date == date, ScheduleSlot.is_booked == False)))
        slots = list(slots)
    if not slots:
        await message.answer("Нет свободных слотов на выбранную дату. Попробуйте другую дату.", reply_markup=get_dates_keyboard())
        return
    kb = [[KeyboardButton(text=slot.time) for slot in slots]]
    kb.append([KeyboardButton(text="/start")])
    await state.set_state(BookingStates.choosing_time)
    await message.answer("Выберите время:", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))

@dp.message(BookingStates.choosing_time)
async def choose_time(message: types.Message, state: FSMContext):
    if message.text == "/start":
        await cmd_start(message, state)
        return
    if not message.text:
        await message.answer("Пожалуйста, выберите время из списка.", reply_markup=BACK_KB)
        return
    data = await state.get_data()
    date = data.get('date')
    time = message.text
    # Проверяем, что слот существует и свободен
    async with SessionLocal() as session:
        slot = await session.scalar(select(ScheduleSlot).where(and_(ScheduleSlot.date == date, ScheduleSlot.time == time, ScheduleSlot.is_booked == False)))
    if not slot:
        await message.answer("Этот слот уже занят или не существует. Выберите другое время.", reply_markup=BACK_KB)
        return
    await state.update_data(time=time)
    await state.set_state(BookingStates.entering_phone)
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Отправить номер телефона", request_contact=True)], [KeyboardButton(text="/start")]],
        resize_keyboard=True
    )
    await message.answer("Введите ваш номер телефона для подтверждения записи или нажмите кнопку:", reply_markup=kb)

@dp.message(BookingStates.entering_phone, F.contact)
async def enter_phone_contact(message: types.Message, state: FSMContext):
    if not message.contact or not message.contact.phone_number:
        await message.answer("Не удалось получить номер телефона. Введите его вручную.", reply_markup=BACK_KB)
        return
    phone = message.contact.phone_number
    await state.update_data(phone=phone)
    data = await state.get_data()
    await state.set_state(BookingStates.confirming)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Подтвердить", callback_data="confirm_yes"),
             InlineKeyboardButton(text="Отменить", callback_data="confirm_no")]
        ]
    )
    await message.answer(f"Проверьте данные:\nИмя: {data['name']}\nДата: {data['date']}\nВремя: {data['time']}\nТелефон: {phone}", reply_markup=kb)

@dp.message(BookingStates.entering_phone)
async def enter_phone(message: types.Message, state: FSMContext):
    if message.text == "/start":
        await cmd_start(message, state)
        return
    if not message.text:
        await message.answer("Пожалуйста, введите номер телефона.", reply_markup=BACK_KB)
        return
    phone = message.text.strip()
    # Проверка только на 89********* или 9*******
    if not re.match(r'^(8|9)\d{9}$', phone):
        await message.answer("Пожалуйста, введите номер в формате 89XXXXXXXXX или 9XXXXXXXXX (только цифры, без +)", reply_markup=BACK_KB)
        return
    await state.update_data(phone=phone)
    data = await state.get_data()
    await state.set_state(BookingStates.confirming)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Подтвердить", callback_data="confirm_yes"),
             InlineKeyboardButton(text="Отменить", callback_data="confirm_no")]
        ]
    )
    await message.answer(f"Проверьте данные:\nИмя: {data['name']}\nДата: {data['date']}\nВремя: {data['time']}\nТелефон: {phone}", reply_markup=kb)

@dp.callback_query(lambda c: c.data in ["confirm_yes", "confirm_no"])
async def process_confirm_callback(callback: types.CallbackQuery, state: FSMContext):
    async def safe_edit_or_answer(text):
        try:
            await callback.message.edit_text(text)
        except Exception:
            await callback.message.answer(text)
    if callback.data == "confirm_no":
        await safe_edit_or_answer("Запись отменена. Вы можете начать заново, выбрав 'Записаться' в меню.")
        await state.clear()
        return
    data = await state.get_data()
    user_id = callback.from_user.id if callback.from_user and callback.from_user.id else None
    if not user_id:
        await safe_edit_or_answer("Ошибка: не удалось определить ваш Telegram ID.")
        await state.clear()
        return
    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.telegram_id == user_id))
        if not user:
            user = User(telegram_id=user_id, phone=data['phone'], is_admin=False)
            session.add(user)
            await session.commit()
        else:
            user.phone = data['phone']
            await session.commit()
        slot = await session.scalar(select(ScheduleSlot).where(and_(ScheduleSlot.date == data['date'], ScheduleSlot.time == data['time'], ScheduleSlot.is_booked == False)))
        if not slot:
            await safe_edit_or_answer("Этот слот уже занят. Попробуйте снова.")
            await state.clear()
            return
        slot.is_booked = True
        booking = Booking(user_id=user.id, slot_id=slot.id)
        booking.name = data['name']
        session.add(booking)
        await session.commit()
    await safe_edit_or_answer("Ваша запись подтверждена! Спасибо! Вы можете записаться ещё раз или вернуться в начало.")
    await state.clear()

@dp.message(Command('admin'))
async def admin_panel(message: types.Message):
    user_id = message.from_user.id if message.from_user and message.from_user.id else None
    if user_id not in ADMIN_IDS:
        await message.answer("Доступ запрещён.")
        return
    kb = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="Посмотреть заявки")],
            [types.KeyboardButton(text="Добавить слот")],
            [types.KeyboardButton(text="Отменить запись")],
            [types.KeyboardButton(text="Очистить старые записи")],
        ], resize_keyboard=True
    )
    await message.answer("Админ-панель:", reply_markup=kb)

@dp.message(lambda m: m.text == "Очистить старые записи")
async def admin_cleanup_old(message: types.Message):
    user_id = message.from_user.id if message.from_user and message.from_user.id else None
    if user_id not in ADMIN_IDS:
        return
    import datetime
    from models import SessionLocal, Booking, ScheduleSlot
    from sqlalchemy import select
    threshold = datetime.date.today() - datetime.timedelta(days=14)
    async with SessionLocal() as session:
        # Удаляем бронирования, у которых дата слота старше 14 дней назад
        old_bookings = await session.execute(
            select(Booking).join(ScheduleSlot, Booking.slot_id == ScheduleSlot.id)
            .where(ScheduleSlot.date < threshold)
        )
        bookings_to_delete = old_bookings.scalars().all()
        for booking in bookings_to_delete:
            await session.delete(booking)
        # Удаляем только те слоты, которые старше 14 дней назад
        old_slots = await session.execute(
            select(ScheduleSlot).where(ScheduleSlot.date < threshold)
        )
        slots_to_delete = old_slots.scalars().all()
        for slot in slots_to_delete:
            await session.delete(slot)
        await session.commit()
    await message.answer("Удалены все записи и слоты, у которых прошло 14 дней с даты записи!")

@dp.message(lambda m: m.text == "Посмотреть заявки")
async def admin_view_bookings(message: types.Message):
    user_id = message.from_user.id if message.from_user and message.from_user.id else None
    if user_id not in ADMIN_IDS:
        return
    async with SessionLocal() as session:
        bookings = await session.execute(
            select(Booking, User, ScheduleSlot)
            .join(User, Booking.user_id == User.id)
            .join(ScheduleSlot, Booking.slot_id == ScheduleSlot.id)
            .order_by(ScheduleSlot.date, ScheduleSlot.time)
        )
        rows = bookings.all()
    if not rows:
        await message.answer("Заявок нет.")
        return
    text = ""
    last_date = None
    for booking, user, slot in rows:
        if last_date != slot.date:
            text += f"\n{'*'*20}\n{slot.date.strftime('%Y-%m-%d')}\n{'*'*20}\n"
            last_date = slot.date
        name = getattr(booking, 'name', None) or getattr(user, 'name', None) or '-'
        text += f"ID: {booking.id}\nИмя: {name}\nВремя: {slot.time}\nТелефон: {user.phone}\n---\n"
    await message.answer(text)

# --- Добавление слотов ---
@dp.message(lambda m: m.text == "Добавить слот")
async def admin_add_slot(message: types.Message, state: FSMContext):
    user_id = message.from_user.id if message.from_user and message.from_user.id else None
    if user_id not in ADMIN_IDS:
        return
    await state.set_state(AdminAddSlotStates.choosing_date)
    today = datetime.date.today()
    dates = [today + datetime.timedelta(days=i) for i in range(14)]
    row = []
    kb = []
    for i, d in enumerate(dates):
        row.append(KeyboardButton(text=d.strftime('%Y-%m-%d')))
        if (i + 1) % 3 == 0 or i == len(dates) - 1:
            kb.append(row)
            row = []
    kb.append([KeyboardButton(text="⬅️ Назад"), KeyboardButton(text="/start")])
    await message.answer("Выберите дату для добавления слотов:", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))

@dp.message(AdminAddSlotStates.choosing_date)
async def admin_add_slot_choose_date(message: types.Message, state: FSMContext):
    if message.text == "/start":
        await cmd_start(message, state)
        return
    if message.text == "⬅️ Назад":
        await cmd_start(message, state)
        return
    try:
        date = datetime.datetime.strptime(message.text, '%Y-%m-%d').date()
    except Exception:
        await message.answer("Пожалуйста, выберите дату из списка.")
        return
    await state.update_data(date=date)
    await state.set_state(AdminAddSlotStates.entering_times)
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="⬅️ Назад"), KeyboardButton(text="/start")]], resize_keyboard=True)
    await message.answer("Введите время для добавления слотов через запятую (например: 10:00, 13:30, 18:45):", reply_markup=kb)

@dp.message(AdminAddSlotStates.entering_times)
async def admin_add_slot_enter_times(message: types.Message, state: FSMContext):
    if message.text == "/start":
        await cmd_start(message, state)
        return
    if message.text == "⬅️ Назад":
        await state.set_state(AdminAddSlotStates.choosing_date)
        today = datetime.date.today()
        dates = [today + datetime.timedelta(days=i) for i in range(14)]
        row = []
        kb = []
        for i, d in enumerate(dates):
            row.append(KeyboardButton(text=d.strftime('%Y-%m-%d')))
            if (i + 1) % 3 == 0 or i == len(dates) - 1:
                kb.append(row)
                row = []
        kb.append([KeyboardButton(text="⬅️ Назад"), KeyboardButton(text="/start")])
        await message.answer("Выберите дату для добавления слотов:", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
        return
    times = [t.strip() for t in message.text.split(",") if t.strip()]
    for t in times:
        if not re.match(r"^\d{2}:\d{2}$", t):
            await message.answer("Некорректный формат времени. Введите, например: 10:00, 13:30, 18:45")
            return
    await state.update_data(times=times)
    data = await state.get_data()
    date = data.get('date')
    await state.set_state(AdminAddSlotStates.confirming)
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="⬅️ Назад"), KeyboardButton(text="/start")]], resize_keyboard=True)
    await message.answer(f"Добавить слоты на {date}: {', '.join(times)}? (да/нет)", reply_markup=kb)

@dp.message(AdminAddSlotStates.confirming)
async def admin_add_slot_confirm(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        await state.set_state(AdminAddSlotStates.entering_times)
        kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="⬅️ Назад"), KeyboardButton(text="/start")]], resize_keyboard=True)
        await message.answer("Введите время для добавления слотов через запятую (например: 10:00, 13:30, 18:45):", reply_markup=kb)
        return
    if message.text == "/start":
        await cmd_start(message, state)
        return
    if not message.text or message.text.lower() not in ["да", "yes", "подтвердить"]:
        await message.answer("Добавление отменено. Хотите добавить ещё слоты? Выберите дату.")
        await state.set_state(AdminAddSlotStates.choosing_date)
        return
    data = await state.get_data()
    date = data.get('date')
    times = data.get('times')
    added = []
    skipped = []
    async with SessionLocal() as session:
        for time in times:
            exists = await session.scalar(
                select(ScheduleSlot).where(ScheduleSlot.date == date, ScheduleSlot.time == time)
            )
            if exists:
                skipped.append(time)
                continue
            slot = ScheduleSlot(date=date, time=time, is_booked=False)
            session.add(slot)
            added.append(time)
        await session.commit()
    msg = f"Добавлены слоты на {date}: {', '.join(added) if added else 'нет новых'}"
    if skipped:
        msg += f"\nПропущены (уже существуют): {', '.join(skipped)}"
    msg += "\n\nХотите добавить ещё слоты? Выберите дату или нажмите /start для выхода в меню."
    await message.answer(msg)
    await state.set_state(AdminAddSlotStates.choosing_date)

# --- Удаление слотов (бирок) ---
@dp.message(lambda m: m.text == "Отменить запись")
async def admin_cancel_booking(message: types.Message, state: FSMContext):
    user_id = message.from_user.id if message.from_user and message.from_user.id else None
    if user_id not in ADMIN_IDS:
        return
    # Получаем даты с заявками
    async with SessionLocal() as session:
        bookings = await session.execute(
            select(Booking, ScheduleSlot)
            .join(ScheduleSlot, Booking.slot_id == ScheduleSlot.id)
            .order_by(ScheduleSlot.date, ScheduleSlot.time)
        )
        rows = bookings.all()
    if not rows:
        await message.answer("Нет заявок для отмены.")
        return
    dates = sorted(set(slot.date for _, slot in rows))
    kb = [[KeyboardButton(text=d.strftime('%Y-%m-%d')) for d in dates]]
    kb.append([KeyboardButton(text="⬅️ Назад"), KeyboardButton(text="/start")])
    await state.set_state(AdminDeleteStates.choosing_date)
    await message.answer("Выберите дату для отмены записи:", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))

@dp.message(AdminDeleteStates.choosing_date)
async def admin_delete_choose_date(message: types.Message, state: FSMContext):
    if message.text == "/start":
        await cmd_start(message, state)
        return
    if message.text == "⬅️ Назад":
        await cmd_start(message, state)
        return
    try:
        date = datetime.datetime.strptime(message.text, '%Y-%m-%d').date()
    except Exception:
        await message.answer("Пожалуйста, выберите дату из списка.")
        return
    await state.update_data(date=date)
    # Получаем слоты с заявками на эту дату
    async with SessionLocal() as session:
        bookings = await session.execute(
            select(Booking, ScheduleSlot)
            .join(ScheduleSlot, Booking.slot_id == ScheduleSlot.id)
            .where(ScheduleSlot.date == date)
            .order_by(ScheduleSlot.time)
        )
        rows = bookings.all()
    if not rows:
        await message.answer("На эту дату нет заявок.")
        await state.set_state(AdminDeleteStates.choosing_date)
        return
    times = [slot.time for _, slot in rows]
    kb = [[KeyboardButton(text=t) for t in times]]
    kb.append([KeyboardButton(text="⬅️ Назад"), KeyboardButton(text="/start")])
    await state.set_state(AdminDeleteStates.choosing_time)
    await message.answer("Выберите время для отмены записи:", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))

@dp.message(AdminDeleteStates.choosing_time)
async def admin_delete_choose_time(message: types.Message, state: FSMContext):
    if message.text == "/start":
        await cmd_start(message, state)
        return
    if message.text == "⬅️ Назад":
        await state.set_state(AdminDeleteStates.choosing_date)
        user_id = message.from_user.id if message.from_user and message.from_user.id else None
        if user_id not in ADMIN_IDS:
            return
        # Получаем даты с заявками
        async with SessionLocal() as session:
            bookings = await session.execute(
                select(Booking, ScheduleSlot)
                .join(ScheduleSlot, Booking.slot_id == ScheduleSlot.id)
                .order_by(ScheduleSlot.date, ScheduleSlot.time)
            )
            rows = bookings.all()
        if not rows:
            await message.answer("Нет заявок для отмены.")
            return
        dates = sorted(set(slot.date for _, slot in rows))
        kb = [[KeyboardButton(text=d.strftime('%Y-%m-%d')) for d in dates]]
        kb.append([KeyboardButton(text="⬅️ Назад"), KeyboardButton(text="/start")])
        await message.answer("Выберите дату для отмены записи:", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
        return
    data = await state.get_data()
    date = data.get('date')
    time = message.text
    # Получаем заявку
    async with SessionLocal() as session:
        booking = await session.scalar(
            select(Booking).join(ScheduleSlot, Booking.slot_id == ScheduleSlot.id)
            .where(ScheduleSlot.date == date, ScheduleSlot.time == time)
        )
        slot = await session.scalar(
            select(ScheduleSlot).where(ScheduleSlot.date == date, ScheduleSlot.time == time)
        )
    if not booking or not slot:
        await message.answer("Заявка не найдена.")
        await state.set_state(AdminDeleteStates.choosing_date)
        return
    await state.update_data(time=time)
    await state.set_state(AdminDeleteStates.confirming)
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="⬅️ Назад"), KeyboardButton(text="/start")]], resize_keyboard=True)
    await message.answer(f"Подтвердить удаление заявки на {date} {time}? (да/нет)", reply_markup=kb)

@dp.message(AdminDeleteStates.confirming)
async def admin_delete_confirm(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        await state.set_state(AdminDeleteStates.choosing_time)
        data = await state.get_data()
        date = data.get('date')
        async with SessionLocal() as session:
            bookings = await session.execute(
                select(Booking, ScheduleSlot)
                .join(ScheduleSlot, Booking.slot_id == ScheduleSlot.id)
                .where(ScheduleSlot.date == date)
                .order_by(ScheduleSlot.time)
            )
            rows = bookings.all()
        if not rows:
            await message.answer("На эту дату нет заявок.")
            await state.set_state(AdminDeleteStates.choosing_date)
            return
        times = [slot.time for _, slot in rows]
        kb = [[KeyboardButton(text=t) for t in times]]
        kb.append([KeyboardButton(text="⬅️ Назад"), KeyboardButton(text="/start")])
        await message.answer("Выберите время для отмены записи:", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
        return
    if message.text == "/start":
        await cmd_start(message, state)
        return
    if not message.text or message.text.lower() not in ["да", "yes", "подтвердить"]:
        await message.answer("Удаление отменено. Хотите удалить ещё? Выберите дату.")
        await state.set_state(AdminDeleteStates.choosing_date)
        return
    data = await state.get_data()
    date = data.get('date')
    time = data.get('time')
    async with SessionLocal() as session:
        booking = await session.scalar(
            select(Booking).join(ScheduleSlot, Booking.slot_id == ScheduleSlot.id)
            .where(ScheduleSlot.date == date, ScheduleSlot.time == time)
        )
        slot = await session.scalar(
            select(ScheduleSlot).where(ScheduleSlot.date == date, ScheduleSlot.time == time)
        )
        if booking:
            await session.delete(booking)
        if slot:
            slot.is_booked = False
        await session.commit()
    await message.answer(f"Заявка на {date} {time} удалена. Хотите удалить ещё? Выберите дату или нажмите /start для выхода.")
    await state.set_state(AdminDeleteStates.choosing_date)

@dp.message(Command('mybookings'))
async def my_bookings(message: types.Message):
    user_id = message.from_user.id if message.from_user and message.from_user.id else None
    if not user_id:
        await message.answer("Ошибка: не удалось определить ваш Telegram ID.")
        return
    async with SessionLocal() as session:
        bookings = await session.execute(
            select(Booking, ScheduleSlot)
            .join(ScheduleSlot, Booking.slot_id == ScheduleSlot.id)
            .where(Booking.user_id == (await session.scalar(select(User.id).where(User.telegram_id == user_id))))
            .order_by(ScheduleSlot.date, ScheduleSlot.time)
        )
        rows = bookings.all()
    if not rows:
        await message.answer("У вас нет активных записей.")
        return
    text = "Ваши записи:\n"
    for booking, slot in rows:
        text += f"Дата: {slot.date.strftime('%Y-%m-%d')} {slot.time}\n"
    await message.answer(text)

@dp.message(Command('exitadmin'))
async def exit_admin(message: types.Message):
    user_id = message.from_user.id if message.from_user and message.from_user.id else None
    if not user_id:
        await message.answer("Ошибка: не удалось определить ваш Telegram ID.")
        return
    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.telegram_id == user_id))
        if user and user.is_admin:
            user.is_admin = False
            await session.commit()
            await message.answer("Вы больше не администратор. Теперь вы обычный пользователь.", reply_markup=types.ReplyKeyboardRemove())
        else:
            await message.answer("У вас нет прав администратора или вы уже обычный пользователь.")

@dp.message(lambda m: m.text == "/start")
async def to_main_menu(message: types.Message, state: FSMContext):
    await cmd_start(message, state)

@dp.message(lambda m: m.text == "Свободные слоты")
async def show_free_slots(message: types.Message):
    async with SessionLocal() as session:
        slots = await session.execute(
            select(ScheduleSlot).where(ScheduleSlot.is_booked == False).order_by(ScheduleSlot.date, ScheduleSlot.time)
        )
        slots = slots.scalars().all()
    if not slots:
        await message.answer("Свободных слотов для записи нет.")
        return
    text = "Свободные слоты для записи:\n"
    last_date = None
    for slot in slots:
        if last_date != slot.date:
            text += f"\n{'*'*20}\n{slot.date.strftime('%Y-%m-%d')}\n{'*'*20}\n"
            last_date = slot.date
        text += f"Время: {slot.time}\n"
    await message.answer(text)

# ... далее будет логика записи, выбора даты/времени, подтверждения и админки ...

if __name__ == '__main__':
    try:
        asyncio.run(dp.start_polling(bot))
    except Exception as e:
        logging.exception("Бот аварийно завершился") 