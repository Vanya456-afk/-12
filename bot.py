import os
import asyncio
import time
import random
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from database import init_db, get_user, collect_money, buy_upgrade, update_stats, do_rebirth, get_top_players

TOKEN = "8906297849:AAHZBlQ-2dipxByhUO-jY22S6zqQ_GiND2c" # Вставь свой токен сюда

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Список построек
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
            [KeyboardButton(text="🔴 Начать стрим"), KeyboardButton(text="🎬 Записать видео")],
            [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="🏆 Топ игроков")],
            [KeyboardButton(text="🔄 Перерождение")]
        ],
        resize_keyboard=True
    )

@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    username = message.from_user.first_name or "Стример"
    await get_user(message.from_user.id, username)
    
    text = (
        "Приветствую тебя, начинающий стример.\n"
        "Прокачивайся, получай деньги, проводи стримы, и поднимайся в топ по балансу!"
    )
    await message.answer(text, reply_markup=main_kb())

@dp.message(F.text == "💰 Забрать прибыль")
async def collect_cmd(message: types.Message):
    earned, total = await collect_money(message.from_user.id)
    await message.answer(f"💵 Вы забрали: **${earned:.1f}**!\n💰 Ваш баланс: **${total:.1f}**", parse_mode="Markdown")

@dp.message(F.text == "👤 Профиль")
async def profile_cmd(message: types.Message):
    username = message.from_user.first_name or "Стример"
    user = await get_user(message.from_user.id, username)
    now = int(time.time())
    
    multiplier = 1 + (user["rebirths"] * 1.0)
    uncollected = (now - user["last_collect"]) * user["income_per_sec"] * multiplier
    
    text = (
        f"👤 **ПРОФИЛЬ СТРИМЕРА: {username}**\n\n"
        f"💰 Баланс: **${user['balance']:.1f}**\n"
        f"👥 Подписчики: **{user['subscribers']}**\n"
        f"⚡️ Базовый доход: **${user['income_per_sec']}/сек**\n"
        f"✨ Множитель дохода: **x{multiplier:.1f}**\n"
        f"📦 В накопителе: **${uncollected:.1f}**\n"
        f"🔄 Перерождений: **{user['rebirths']}**"
    )
    await message.answer(text, parse_mode="Markdown")

@dp.message(F.text == "🔴 Начать стрим")
async def stream_cmd(message: types.Message):
    username = message.from_user.first_name or "Стример"
    user = await get_user(message.from_user.id, username)
    
    # Шанс события
    event_type = random.choices(["donat", "collab", "quiet"], weights=[60, 20, 20])[0]
    
    if event_type == "collab" and (user["subscribers"] >= 500 or user["rebirths"] > 0):
        reward = random.randint(300, 1500) * (user["rebirths"] + 1)
        subs = random.randint(50, 200)
        await update_stats(message.from_user.id, add_balance=reward, add_subs=subs)
        msg = f"🤝 **КОЛЛАБОРАЦИЯ!** Известный бренд предложил вам интеграцию на стриме!\n➕ Получено: **${reward}** и **+{subs} подписчиков**!"
    elif event_type == "donat":
        reward = random.randint(50, 400) * (user["rebirths"] + 1)
        subs = random.randint(10, 50)
        await update_stats(message.from_user.id, add_balance=reward, add_subs=subs)
        msg = f"💸 **ДОНАТ!** Щедрый зритель задонатил вам на стриме!\n➕ Получено: **${reward}** и **+{subs} подписчиков**!"
    else:
        subs = random.randint(5, 20)
        await update_stats(message.from_user.id, add_subs=subs)
        msg = f"🎥 Стрим прошёл спокойно. Вы привлекли **+{subs} новых подписчиков**!"
        
    await message.answer(msg, parse_mode="Markdown")

@dp.message(F.text == "🎬 Записать видео")
async def video_cmd(message: types.Message):
    subs = random.randint(15, 60)
    money = random.randint(20, 100)
    await update_stats(message.from_user.id, add_balance=money, add_subs=subs)
    
    await message.answer(
        f"🎬 Вы смонтировали и выложили новое видео!\n"
        f"📈 Оно набрало просмотры: **+{subs} подписчиков** и **+${money} с монетизации**!",
        parse_mode="Markdown"
    )

@dp.message(F.text == "🏆 Топ игроков")
async def top_cmd(message: types.Message):
    top_players = await get_top_players()
    
    text = "🏆 **ТОП-10 СТРИМЕРОВ ПО БАЛАНСУ**\n\n"
    for idx, (name, balance, subs) in enumerate(top_players, 1):
        text += f"{idx}. **{name}** — ${balance:.1f} | 👥 {subs} подп.\n"
        
    await message.answer(text, parse_mode="Markdown")

@dp.message(F.text == "🔄 Перерождение")
async def rebirth_cmd(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Сделать Rebirth", callback_data="do_rebirth")]
    ])
    text = (
        "🔄 **СИСТЕМА ПЕРЕРОЖДЕНИЯ (REBIRTH)**\n\n"
        "Сбрось свой баланс и покупки, чтобы получить **постоянный множитель дохода (x2, x3 и т.д.)**!\n\n"
        "📌 **Требования:**\n"
        "• Куплены все улучшения в магазине (Этап 5)\n"
        "• $10,000 на балансе"
    )
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data == "do_rebirth")
async def rebirth_callback(callback: types.CallbackQuery):
    success, msg = await do_rebirth(callback.from_user.id)
    await callback.answer(msg, show_alert=True)
    if success:
        await callback.message.edit_text("🎉 Вы совершили Перерождение! Поздравляем!")

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
        await message.answer("🎉 Вы купили все доступные улучшения! Теперь вам доступно **Перерождение**!")

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
