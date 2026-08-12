import asyncio
import logging
import aiosqlite
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

TOKEN = "8994773003:AAHqmGBN_HEyOHkH18DF9uXmigfigWUvfSc"
ADMIN_ID = 5006344380

logging.basicConfig(level=logging.INFO)
router = Router()
storage = MemoryStorage()

# Состояния записи
class BookState(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_car = State()

async def init_db():
    async with aiosqlite.connect("crm.db") as db:
        await db.execute("CREATE TABLE IF NOT EXISTS users (tg_id INTEGER PRIMARY KEY, name TEXT, phone TEXT, car TEXT)")
        await db.commit()

def main_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📅 Записаться на осмотр"), KeyboardButton(text="👤 Мой профиль")],
            [KeyboardButton(text="🖼 Галерея работ"), KeyboardButton(text="📞 Связаться с мастером")]
        ], 
        resize_keyboard=True
    )

@router.message(Command("start"))
async def start(message: Message):
    await message.answer("✨ *VIP-Детейлинг приветствует вас!*\nВыберите действие:", parse_mode="Markdown", reply_markup=main_kb())

# --- ЛОГИКА ЗАПИСИ ---
@router.message(F.text == "📅 Записаться на осмотр")
async def start_booking(message: Message, state: FSMContext):
    await message.answer("👤 *Давайте начнем!* Как к вам обращаться?", parse_mode="Markdown")
    await state.set_state(BookState.waiting_for_name)

@router.message(BookState.waiting_for_name)
async def get_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("📱 Введите ваш номер телефона:")
    await state.set_state(BookState.waiting_for_phone)

@router.message(BookState.waiting_for_phone)
async def get_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await message.answer("🚗 Укажите марку и модель вашего автомобиля:")
    await state.set_state(BookState.waiting_for_car)

@router.message(BookState.waiting_for_car)
async def get_car(message: Message, state: FSMContext):
    data = await state.update_data(car=message.text)
    async with aiosqlite.connect("crm.db") as db:
        await db.execute("INSERT OR REPLACE INTO users (tg_id, name, phone, car) VALUES (?, ?, ?, ?)", 
                         (message.from_user.id, data['name'], data['phone'], data['car']))
        await db.commit()
    
    msg = f"✅ *Отлично, {data['name']}!*\nМы записали вас на осмотр.\n\n👤 Имя: {data['name']}\n📱 Телефон: {data['phone']}\n🚗 Авто: {data['car']}"
    await message.answer(msg, parse_mode="Markdown", reply_markup=main_kb())
    await message.bot.send_message(ADMIN_ID, f"🔔 *Новая запись на осмотр!*\n\n{msg}", parse_mode="Markdown")
    await state.clear()

# --- ПРОЧИЕ КНОПКИ ---
@router.message(F.text == "🖼 Галерея работ")
async def gallery(message: Message):
    await message.answer("📸 *Наши работы:* [здесь будут фото]", parse_mode="Markdown")

@router.message(F.text == "👤 Мой профиль")
async def profile(message: Message):
    await message.answer("👤 *Ваш профиль:* ...", parse_mode="Markdown")

@router.message(F.text == "📞 Связаться с мастером")
async def contact(message: Message):
    await message.answer("📞 *Наш телефон:* +7 (XXX) XXX-XX-XX\nНаписать: @famsheat", parse_mode="Markdown")

async def main():
    await init_db()
    bot = Bot(token=TOKEN)
    dp = Dispatcher(storage=storage)
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
