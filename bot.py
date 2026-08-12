import asyncio
import logging
import aiosqlite
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command

# Твой токен
TOKEN = "8994773003:AAHqmGBN_HEyOHkH18DF9uXmigfigWUvfSc"
ADMIN_ID = 5006344380

logging.basicConfig(level=logging.INFO)
router = Router()

# --- ИНИЦИАЛИЗАЦИЯ БД ---
async def init_db():
    async with aiosqlite.connect("crm.db") as db:
        await db.execute("CREATE TABLE IF NOT EXISTS users (tg_id INTEGER PRIMARY KEY, name TEXT, phone TEXT, car TEXT)")
        await db.execute("CREATE TABLE IF NOT EXISTS portfolio (id INTEGER PRIMARY KEY, photo_url TEXT, description TEXT)")
        await db.commit()

# --- КЛАВИАТУРА ---
def main_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📅 Записаться на осмотр"), KeyboardButton(text="👤 Мой профиль")],
            [KeyboardButton(text="🖼 Галерея работ"), KeyboardButton(text="📞 Связаться с мастером")]
        ], 
        resize_keyboard=True
    )

# --- ОБРАБОТЧИКИ ---
@router.message(Command("start"))
async def start(message: Message):
    await message.answer(
        "✨ *VIP-Детейлинг приветствует вас!*\nВыберите нужный раздел в меню:", 
        parse_mode="Markdown", 
        reply_markup=main_kb()
    )

@router.message(F.text == "🖼 Галерея работ")
async def gallery(message: Message):
    await message.answer("📸 *Примеры наших работ:*\n[Здесь вы сможете посмотреть фото до/после]", parse_mode="Markdown")

@router.message(F.text == "👤 Мой профиль")
async def profile(message: Message):
    await message.answer("👤 *Ваш профиль:*\n\nЗдесь будет информация о вашем авто.", parse_mode="Markdown")

@router.message(F.text == "📞 Связаться с мастером")
async def contact(message: Message):
    await message.answer("📞 *Наш телефон:* +7 (XXX) XXX-XX-XX\nИли напишите нам напрямую: @famsheat", parse_mode="Markdown")

# --- ЗАПУСК ---
async def main():
    await init_db()
    bot = Bot(token=TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
