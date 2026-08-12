import asyncio, logging, aiosqlite
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

TOKEN = "8994773003:AAHqmGBN_HEyOHkH18DF9uXmigfigWUvfSc"
ADMIN_ID = 5006344380

router = Router()

class BookState(StatesGroup):
    choosing_date = State()
    choosing_time = State()
    name = State()
    phone = State()
    car = State()

async def init_db():
    async with aiosqlite.connect("crm.db") as db:
        await db.execute("CREATE TABLE IF NOT EXISTS schedule (id INTEGER PRIMARY KEY, date TEXT, time TEXT, is_booked INTEGER DEFAULT 0)")
        await db.execute("CREATE TABLE IF NOT EXISTS users (tg_id INTEGER, name TEXT, phone TEXT, car TEXT, datetime TEXT)")
        await db.commit()

# --- АДМИН: Добавление слота ---
@router.message(Command("add_slot"))
async def add_slot(message: Message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split(" ") # /add_slot 25.10 14:00
    await db_exec("INSERT INTO schedule (date, time, is_booked) VALUES (?, ?, 0)", (args[1], args[2]))
    await message.answer(f"✅ Добавлен слот: {args[1]} в {args[2]}")

# --- КЛИЕНТ: Выбор даты ---
@router.message(F.text == "📅 Записаться на осмотр")
async def show_dates(message: Message, state: FSMContext):
    async with aiosqlite.connect("crm.db") as db:
        async with db.execute("SELECT DISTINCT date FROM schedule WHERE is_booked = 0") as cursor:
            dates = await cursor.fetchall()
    kb = [[InlineKeyboardButton(text=d[0], callback_data=f"date_{d[0]}")] for d in dates]
    await message.answer("📅 Выберите дату:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

# --- КЛИЕНТ: Выбор времени ---
@router.callback_query(F.data.startswith("date_"))
async def show_times(query: CallbackQuery, state: FSMContext):
    date = query.data.split("_")[1]
    await state.update_data(date=date)
    async with aiosqlite.connect("crm.db") as db:
        async with db.execute("SELECT id, time FROM schedule WHERE date = ? AND is_booked = 0", (date,)) as cursor:
            times = await cursor.fetchall()
    kb = [[InlineKeyboardButton(text=t[1], callback_data=f"slot_{t[0]}")] for t in times]
    await query.message.edit_text("🕒 Выберите время:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

# --- ЗАПИСЬ ---
@router.callback_query(F.data.startswith("slot_"))
async def book_slot(query: CallbackQuery, state: FSMContext):
    slot_id = query.data.split("_")[1]
    await state.update_data(slot_id=slot_id)
    # БРОНИРУЕМ СРАЗУ, чтобы никто другой не занял
    async with aiosqlite.connect("crm.db") as db:
        await db.execute("UPDATE schedule SET is_booked = 1 WHERE id = ?", (slot_id,))
        await db.commit()
    await query.message.answer("👤 Как вас зовут?")
    await state.set_state(BookState.name)

# ... (далее функции получения name, phone, car и сохранение в users)

async def main():
    await init_db()
    bot = Bot(token=TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
