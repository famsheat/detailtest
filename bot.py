import asyncio, logging, aiosqlite
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

TOKEN = "8994773003:AAHqmGBN_HEyOHkH18DF9uXmigfigWUvfSc"
ADMIN_ID = 5006344380

logging.basicConfig(level=logging.INFO)
router = Router()
dp = Dispatcher(storage=MemoryStorage())

class BookState(StatesGroup):
    name = State()
    phone = State()
    car = State()

async def init_db():
    async with aiosqlite.connect("crm.db") as db:
        await db.execute("CREATE TABLE IF NOT EXISTS schedule (id INTEGER PRIMARY KEY, date TEXT, time TEXT, is_booked INTEGER DEFAULT 0)")
        await db.execute("CREATE TABLE IF NOT EXISTS users (tg_id INTEGER PRIMARY KEY, name TEXT, phone TEXT, car TEXT)")
        await db.execute("CREATE TABLE IF NOT EXISTS appointments (name TEXT, phone TEXT, car TEXT, datetime TEXT, service TEXT)")
        await db.commit()

# --- КЛИЕНТСКИЕ КОМАНДЫ ---
@router.message(Command("start"))
async def start(message: Message):
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📅 Записаться на осмотр"), KeyboardButton(text="👤 Мой профиль")],
        [KeyboardButton(text="🖼 Галерея работ"), KeyboardButton(text="📞 Связаться с мастером")]
    ], resize_keyboard=True)
    await message.answer("✨ *VIP-Детейлинг приветствует!*\nВыберите действие:", parse_mode="Markdown", reply_markup=kb)

@router.message(F.text == "📅 Записаться на осмотр")
async def show_dates(message: Message):
    async with aiosqlite.connect("crm.db") as db:
        async with db.execute("SELECT DISTINCT date FROM schedule WHERE is_booked = 0") as cursor:
            dates = await cursor.fetchall()
    if not dates: await message.answer("❌ Нет свободных дат.")
    else:
        kb = [[InlineKeyboardButton(text=d[0], callback_data=f"date_{d[0]}")] for d in dates]
        await message.answer("📅 Выберите дату:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@router.callback_query(F.data.startswith("date_"))
async def show_times(query: CallbackQuery):
    date = query.data.split("_")[1]
    async with aiosqlite.connect("crm.db") as db:
        async with db.execute("SELECT id, time FROM schedule WHERE date = ? AND is_booked = 0", (date,)) as cursor:
            times = await cursor.fetchall()
    kb = [[InlineKeyboardButton(text=t[1], callback_data=f"slot_{t[0]}")] for t in times]
    await query.message.edit_text("🕒 Выберите время:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@router.callback_query(F.data.startswith("slot_"))
async def book_slot(query: CallbackQuery, state: FSMContext):
    slot_id = query.data.split("_")[1]
    await state.update_data(slot_id=slot_id)
    async with aiosqlite.connect("crm.db") as db:
        time = await db.execute_scalar("SELECT date || ' в ' || time FROM schedule WHERE id = ?", (slot_id,))
        await state.update_data(datetime=time)
    await query.message.answer("👤 Как вас зовут?")
    await state.set_state(BookState.name)

@router.message(BookState.name)
async def get_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("📱 Введите номер телефона:")
    await state.set_state(BookState.phone)

@router.message(BookState.phone)
async def get_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await message.answer("🚗 Марка и модель авто:")
    await state.set_state(BookState.car)

@router.message(BookState.car)
async def finish(message: Message, state: FSMContext):
    data = await state.update_data(car=message.text)
    async with aiosqlite.connect("crm.db") as db:
        await db.execute("UPDATE schedule SET is_booked = 1 WHERE id = ?", (data['slot_id'],))
        await db.execute("INSERT INTO appointments VALUES (?, ?, ?, ?, ?, ?)", (data['name'], data['phone'], data['car'], data['datetime'], "Осмотр", 4000))
        await db.commit()
    await message.answer("🎉 Запись подтверждена!")
    await message.bot.send_message(ADMIN_ID, f"🔔 *Новая запись!*\n{data['name']}, {data['phone']}, {data['car']}, {data['datetime']}")
    await state.clear()

# --- АДМИНСКИЕ КОМАНДЫ ---
@router.message(Command("add"))
async def add_slot(message: Message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split(" ")
    async with aiosqlite.connect("crm.db") as db:
        await db.execute("INSERT INTO schedule (date, time, is_booked) VALUES (?, ?, 0)", (args[1], args[2]))
        await db.commit()
    await message.answer(f"✅ Добавлен слот: {args[1]} {args[2]}")

@router.message(Command("send"))
async def send_promo(message: Message):
    if message.from_user.id != ADMIN_ID: return
    text = message.text.replace("/send ", "")
    async with aiosqlite.connect("crm.db") as db:
        async with db.execute("SELECT tg_id FROM users") as cursor:
            users = await cursor.fetchall()
            for u in users:
                try: await message.bot.send_message(u[0], text)
                except: continue
    await message.answer("✅ Рассылка завершена.")

async def main():
    await init_db()
    bot = Bot(token=TOKEN)
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
