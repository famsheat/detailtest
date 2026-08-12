import asyncio, logging, aiosqlite
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

TOKEN = "8994773003:AAHqmGBN_HEyOHkH18DF9uXmigfigWUvfSc"
ADMIN_ID = 5006344380
ADDRESS = "г. Казань, ул. Аделя Кутуя, 110дк4"
MAP_LINK = "https://yandex.ru/maps/?text=Казань%2C%20улица%20Аделя%20Кутуя%2C%20110дк4"

logging.basicConfig(level=logging.INFO)
router = Router()
storage = MemoryStorage()

class BookState(StatesGroup):
    name = State()
    phone = State()
    car = State()

class EditState(StatesGroup):
    value = State()

async def init_db():
    async with aiosqlite.connect("crm.db") as db:
        await db.execute("CREATE TABLE IF NOT EXISTS schedule (id INTEGER PRIMARY KEY, date TEXT, time TEXT, is_booked INTEGER DEFAULT 0)")
        await db.execute("CREATE TABLE IF NOT EXISTS users (tg_id INTEGER PRIMARY KEY, name TEXT, phone TEXT, car TEXT)")
        await db.execute("CREATE TABLE IF NOT EXISTS appointments (name TEXT, phone TEXT, car TEXT, datetime TEXT, service TEXT)")
        await db.commit()

def main_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📅 Записаться на осмотр"), KeyboardButton(text="👤 Мой профиль")],
        [KeyboardButton(text="🖼 Галерея работ"), KeyboardButton(text="📍 Наш адрес")],
        [KeyboardButton(text="📞 Связаться с мастером")]
    ], resize_keyboard=True)

@router.message(Command("start"))
async def start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("✨ *VIP-Детейлинг приветствует!*\nВыберите действие:", parse_mode="Markdown", reply_markup=main_kb())

# --- ЗАПИСЬ ---
@router.message(F.text == "📅 Записаться на осмотр")
async def show_dates(message: Message):
    async with aiosqlite.connect("crm.db") as db:
        async with db.execute("SELECT DISTINCT date FROM schedule WHERE is_booked = 0") as cursor:
            dates = await cursor.fetchall()
    if not dates:
        await message.answer("❌ Нет доступных дат.")
    else:
        kb = [[InlineKeyboardButton(text=d[0], callback_data=f"date_{d[0]}")] for d in dates]
        await message.answer("📅 Выберите дату:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@router.callback_query(F.data.startswith("date_"))
async def show_times(query: CallbackQuery):
    await query.answer()
    date = query.data.split("_")[1]
    async with aiosqlite.connect("crm.db") as db:
        async with db.execute("SELECT id, time FROM schedule WHERE date = ? AND is_booked = 0", (date,)) as cursor:
            times = await cursor.fetchall()
    kb = [[InlineKeyboardButton(text=t[1], callback_data=f"slot_{t[0]}")] for t in times]
    await query.message.edit_text("🕒 Выберите время:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@router.callback_query(F.data.startswith("slot_"))
async def book_slot(query: CallbackQuery, state: FSMContext):
    await query.answer()
    slot_id = query.data.split("_")[1]
    await state.update_data(slot_id=slot_id)
    async with aiosqlite.connect("crm.db") as db:
        cursor = await db.execute("SELECT date || ' в ' || time FROM schedule WHERE id = ?", (slot_id,))
        row = await cursor.fetchone()
        await state.update_data(datetime=row[0] if row else "не указано")
    await query.message.answer("👤 Время выбрано. Как вас зовут?")
    await state.set_state(BookState.name)

@router.message(StateFilter(BookState.name))
async def get_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("📱 Введите номер телефона:")
    await state.set_state(BookState.phone)

@router.message(StateFilter(BookState.phone))
async def get_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await message.answer("🚗 Марка и модель авто:")
    await state.set_state(BookState.car)

@router.message(StateFilter(BookState.car))
async def finish(message: Message, state: FSMContext):
    data = await state.get_data()
    user_car = message.text
    async with aiosqlite.connect("crm.db") as db:
        await db.execute("UPDATE schedule SET is_booked = 1 WHERE id = ?", (data['slot_id'],))
        await db.execute("INSERT OR REPLACE INTO users (tg_id, name, phone, car) VALUES (?, ?, ?, ?)", 
                         (message.from_user.id, data['name'], data['phone'], user_car))
        await db.execute("INSERT INTO appointments VALUES (?, ?, ?, ?, ?)", 
                         (data['name'], data['phone'], user_car, data['datetime'], "Осмотр"))
        await db.commit()
    
    msg = (f"🎉 *Запись подтверждена!*\n\n"
           f"👤 Имя: {data['name']}\n📱 Тел: {data['phone']}\n"
           f"🚗 Авто: {user_car}\n📅 Время: {data['datetime']}\n\n"
           f"📍 Ждем вас: *{ADDRESS}*\n[🗺 Открыть на карте]({MAP_LINK})")
    await message.answer(msg, parse_mode="Markdown")
    
    admin_msg = (f"🔔 *НОВАЯ ЗАПИСЬ!* 🔔\n\n"
                 f"👤 Клиент: {data['name']}\n"
                 f"📱 Тел: `{data['phone']}`\n"
                 f"🚗 Авто: {user_car}\n"
                 f"📅 Время: *{data['datetime']}*\n\n"
                 f"💬 [Написать клиенту](tg://user?id={message.from_user.id})")
    await message.bot.send_message(ADMIN_ID, admin_msg, parse_mode="Markdown")
    await state.clear()

# --- ПРОФИЛЬ ---
@router.message(F.text == "👤 Мой профиль")
async def profile(message: Message, state: FSMContext):
    await state.clear()
    async with aiosqlite.connect("crm.db") as db:
        cursor = await db.execute("SELECT name, phone, car FROM users WHERE tg_id = ?", (message.from_user.id,))
        user = await cursor.fetchone()
    if user:
        text = f"👤 *Ваш профиль:*\n\nИмя: {user[0]}\nТелефон: {user[1]}\nАвто: {user[2]}"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Изменить имя", callback_data="edit_name")],
            [InlineKeyboardButton(text="📱 Изменить телефон", callback_data="edit_phone")],
            [InlineKeyboardButton(text="🚗 Изменить авто", callback_data="edit_car")]
        ])
        await message.answer(text, parse_mode="Markdown", reply_markup=kb)
    else:
        await message.answer("👤 Данные пусты. Запишитесь на осмотр!")

@router.callback_query(F.data.startswith("edit_"))
async def edit_profile(query: CallbackQuery, state: FSMContext):
    await query.answer()
    field = query.data.split("_")[1]
    await state.update_data(field=field)
    prompts = {"name": "Введите новое имя:", "phone": "Введите новый телефон:", "car": "Введите новое авто:"}
    await query.message.answer(prompts[field])
    await state.set_state(EditState.value)

@router.message(StateFilter(EditState.value))
async def save_edit(message: Message, state: FSMContext):
    data = await state.get_data()
    field = data['field']
    async with aiosqlite.connect("crm.db") as db:
        await db.execute(f"UPDATE users SET {field} = ? WHERE tg_id = ?", (message.text, message.from_user.id))
        await db.commit()
    await message.answer(f"✅ Обновлено!")
    await state.clear()

# --- АДРЕС и ПРОЧИЕ КНОПКИ ---
@router.message(F.text == "📍 Наш адрес")
async def address(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🗺 Открыть карту", url=MAP_LINK)]])
    await message.answer(f"📍 *Мы находимся:*\n{ADDRESS}", parse_mode="Markdown", reply_markup=kb)

@router.message(F.text == "🖼 Галерея работ")
async def gallery(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Перейти в канал 📸", url="https://t.me/ledexpertkzn")]])
    await message.answer("📸 *Наши работы:*", parse_mode="Markdown", reply_markup=kb)

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
    await message.answer(f"✅ Слот {args[1]} {args[2]} добавлен.")

async def main():
    await init_db()
    bot = Bot(token=TOKEN)
    dp = Dispatcher(storage=storage)
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
