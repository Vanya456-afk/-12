import os
import asyncio
import time
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from database import init_db, get_user, collect_money, buy_upgrade

TOKEN = "8906297849:AAHZBlQ-2dipxByhUO-jY22S6zqQ_GiND2c"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Список построек (магазин тайкуна)
UPGRADES = {
    1: {"name": "💻 Б/У Ноутбук", "cost": 100, "income": 3},
    2: {"name": "🎙 Дешевый микрофон", "cost": 300, "income": 8},
    3: {"name": "💡 Кольцевая лампа", "cost": 750, "income": 20},
    4: {"name": "🖥 Игровой ПК", "cost": 2000, "income": 50},
}

def main_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💰 Забрать прибыль"), KeyboardButton(text="🏬 Магазин")],
            [KeyboardButton(text="📊 Студия")]
        ],
        resize_keyboard=True
    )

@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    await get_user(message.from_user.id)
    await message.answer("🎬 Добро пожаловать в Ютуб-Тайкун! Развивай студию и качай доход.", reply_markup=main_kb())

@dp.message(F.text == "💰 Забрать прибыль")
async def collect_cmd(message: types.Message):
    earned, total = await collect_money(message.from_user.id)
    await message.answer(f"💵 Вы забрали: **${earned:.1f}**!\n💰 Ваш баланс: **${total:.1f}**", parse_mode="Markdown")

@dp.message(F.text == "📊 Студия")
async def stats_cmd(message: types.Message):
    user = await get_user(message.from_user.id)
    now = int(time.time())
    uncollected = (now - user["last_collect"]) * user["income_per_sec"]
    
    text = (
        f"🎙 **ТВОЯ СТУДИЯ**\n\n"
        f"💵 Баланс: **${user['balance']:.1f}**\n"
        f"⚡️ Доход: **${user['income_per_sec']}/сек**\n"
        f"📦 В накопителе: **${uncollected:.1f}**\n"
        f"🏗 Этап стройки: **{user['stage']}**"
    )
    await message.answer(text, parse_mode="Markdown")

@dp.message(F.text == "🏬 Магазин")
async def shop_cmd(message: types.Message):
    user = await get_user(message.from_user.id)
    stage = user["stage"]
    
    if stage in UPGRADES:
        item = UPGRADES[stage]
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"Купить за ${item['cost']}", callback_data=f"buy_{stage}")]
        ])
        await message.answer(f"📦 **Следом по плану:** {item['name']}\n➕ Доход: +${item['income']}/сек\n💵 Цена: ${item['cost']}", reply_markup=kb, parse_mode="Markdown")
    else:
        await message.answer("🎉 Вы купили все доступные улучшения для этой студии!")

@dp.callback_query(F.data.startswith("buy_"))
async def buy_callback(callback: types.CallbackQuery):
    stage = int(callback.data.split("_")[1])
    item = UPGRADES[stage]
    
    success, msg = await buy_upgrade(callback.from_user.id, item['cost'], item['income'], stage + 1)
    await callback.answer(msg, show_alert=True)
    if success:
        await callback.message.edit_text(f"✅ Успешно куплено: {item['name']}!")

async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
