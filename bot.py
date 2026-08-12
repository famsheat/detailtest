import asyncio, logging, aiosqlite
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove, InputMediaPhoto, InputMediaVideo
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

TOKEN = "8994773003:AAHqmGBN_HEyOHkH18DF9uXmigfigWUvfSc"
ADMIN_ID = 5006344380

logging.basicConfig(level=logging.INFO)
router = Router()
storage = MemoryStorage()

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

def main_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📅 Записаться на осмотр"), KeyboardButton(text="👤 Мой профиль")],
        [KeyboardButton(text="🖼 Галерея работ"), KeyboardButton(text="📞 Связаться с мастером")]
    ], resize_keyboard=True)

@router.message(Command("start"))
async def start(message: Message):
    await message.answer("✨ *VIP-Детейлинг приветствует!*\nВыберите действие:", parse_mode="Markdown", reply_markup=main_kb())

# --- ЗАПИСЬ ---
@router.message(F.text == "📅 Записаться на осмотр")
async def show_dates(message: Message):
    async with aiosqlite.connect("crm.db") as db:
        async with db.execute("SELECT DISTINCT date FROM schedule WHERE is_booked = 0") as cursor:
            dates = await cursor.fetchall()
    if not dates: await message.answer("❌ Нет доступных дат.")
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
        await db.execute("INSERT OR REPLACE INTO users (tg_id, name, phone, car) VALUES (?, ?, ?, ?)", (message.from_user.id, data['name'], data['phone'], data['car']))
        await db.execute("INSERT INTO appointments VALUES (?, ?, ?, ?, ?, ?)", (data['name'], data['phone'], data['car'], data['datetime'], "Осмотр", "4000₽"))
        await db.commit()
    await message.answer("🎉 Запись подтверждена!")
    await message.bot.send_message(ADMIN_ID, f"🔔 *Новая запись!*\n{data['name']}, {data['phone']}, {data['car']}, {data['datetime']}", parse_mode="Markdown")
    await state.clear()

# --- ПРОФИЛЬ И ГАЛЕРЕЯ ---
@router.message(F.text == "🖼 Галерея работ")
async def gallery(message: Message):
    # ЗАМЕНИ file_id на свои (получи их через @userinfobot, отправив ему фото)
    media = [
        InputMediaPhoto(media="AgACAgIAAxkBAA..."), 
        InputMediaVideo(media="BAACAgIAAxkBAA...")
    ]
    try: await message.answer_media_group(media=media)
    except: await message.answer("📸 *Галерея пока в процессе наполнения!*", parse_mode="Markdown")

@router.message(F.text == "👤 Мой профиль")
async def profile(message: Message):
    async with aiosqlite.connect("crm.db") as db:
        user = await db.execute_scalar("SELECT name || ', ' || car FROM users WHERE tg_id = ?", (message.from_user.id,))
    await message.answer(f"👤 *Ваш профиль:*\n{user or 'Не заполнен'}", parse_mode="Markdown")

@router.message(F.text == "📞 Связаться с мастером")
async def contact(message: Message):
    await message.answer("📞 *Наш телефон:* +7 (XXX) XXX-XX-XX\nНаписать: @famsheat", parse_mode="Markdown")

@router.message(Command("add"))
async def add_slot(message: Message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split(" ")
    async with aiosqlite.connect("crm.db") as db:
        await db.execute("INSERT INTO schedule (date, time, is_booked) VALUES (?, ?, 0)", (args[1], args[2]))
        await db.commit()
    await message.answer(f"✅ Добавлен слот: {args[1]} {args[2]}")

async def main():
    await init_db()
    bot = Bot(token=TOKEN)
    dp = Dispatcher(storage=storage)
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
