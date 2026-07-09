import os
import asyncio
import time
import random
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from database import (
    init_db, get_user, collect_money, buy_upgrade, buy_worker, 
    update_stats, do_rebirth, get_top_players, open_daily_case, CATEGORIES
)

TOKEN = "8906297849:AAHZBlQ-2dipxByhUO-jY22S6zqQ_GiND2c" # Вставь сюда свой токен!

bot = Bot(token=TOKEN)
dp = Dispatcher()

def get_daily_trend():
    day_seed = int(time.strftime("%Y%m%d"))
    random.seed(day_seed)
    trend = random.choice(CATEGORIES)
    random.seed()
    return trend

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
            [KeyboardButton(text="👔 Команда"), KeyboardButton(text="🔥 Устроить скандал")],
            [KeyboardButton(text="🎁 Посылка"), KeyboardButton(text="🔥 Тренд дня")],
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
        "Прокачивайся, получай деньги, нанимай команду и поджигай интернет драмами!"
    )
    await message.answer(text, reply_markup=main_kb())

@dp.message(F.text == "🔥 Тренд дня")
async def trend_cmd(message: types.Message):
    trend = get_daily_trend()
    text = f"🔥 **ТРЕНД СЕГОДНЯШНЕГО ДНЯ:** **{trend}**!\n\n⚡️ Делай контент по этой теме, чтобы получать **x2 к деньгам и подписчикам**!"
    await message.answer(text, parse_mode="Markdown")

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
    
    editor_status = "✅ Есть" if user["has_editor"] else "❌ Нет"
    manager_status = "✅ Есть" if user["has_manager"] else "❌ Нет"
    
    text = (
        f"👤 **ПРОФИЛЬ СТРИМЕРА: {username}**\n\n"
        f"💰 Баланс: **${user['balance']:.1f}**\n"
        f"👥 Подписчики: **{user['subscribers']}**\n"
        f"⚡️ Базовый доход: **${user['income_per_sec']}/сек**\n"
        f"✨ Множитель: **x{multiplier:.1f}**\n"
        f"📦 В накопителе: **${uncollected:.1f}**\n"
        f"🚨 Страйки: **{user['strikes']}/3**\n\n"
        f"👔 **Команда:** Монтажёр ({editor_status}) | Менеджер ({manager_status})\n"
        f"🔄 Перерождений: **{user['rebirths']}**"
    )
    await message.answer(text, parse_mode="Markdown")

# 👔 МЕХАНИКА 1: КОМАНДА
@dp.message(F.text == "👔 Команда")
async def team_cmd(message: types.Message):
    user = await get_user(message.from_user.id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎬 Нанять Монтажёра ($1,500)", callback_data="buy_editor")],
        [InlineKeyboardButton(text="💼 Нанять Менеджера ($3,500)", callback_data="buy_manager")]
    ])
    text = (
        "👔 **НАЁМНАЯ КОМАНДА**\n\n"
        "🎬 **Монтажёр:** Увеличивает доход от ваших видео в 2 раза!\n"
        "💼 **Менеджер:** Приносит +$15/сек пассивного дохода от рекламы!\n\n"
        f"Твой баланс: **${user['balance']:.1f}**"
    )
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data == "buy_editor")
async def editor_callback(callback: types.CallbackQuery):
    success, msg = await buy_worker(callback.from_user.id, "editor", 1500)
    await callback.answer(msg, show_alert=True)
    if success:
        await callback.message.edit_text("✅ Вы наняли Монтажёра! Видео теперь приносят х2 дохода!")

@dp.callback_query(F.data == "buy_manager")
async def manager_callback(callback: types.CallbackQuery):
    success, msg = await buy_worker(callback.from_user.id, "manager", 3500)
    if success:
        # Добавляем к базовому доходу
        await buy_upgrade(callback.from_user.id, 0, 15, 0)
        await callback.message.edit_text("✅ Вы наняли Менеджера! Доход вырос на +$15/сек!")
    else:
        await callback.answer(msg, show_alert=True)

# 💥 МЕХАНИКА 2: СКАНДАЛЫ И СТРАЙКИ
@dp.message(F.text == "🔥 Устроить скандал")
async def drama_cmd(message: types.Message):
    user = await get_user(message.from_user.id)
    
    if user["strikes"] >= 3:
        await message.answer("🚨 У тебя **3/3 Страйка**! Ютуб заблокировал тебе возможность устраивать драмы до Перерождения!")
        return

    # Шанс: 60% успех (хайп), 40% провал (страйк)
    outcome = random.choices(["hype", "strike"], weights=[60, 40])[0]
    
    if outcome == "hype":
        gained_subs = random.randint(150, 600) * (user["rebirths"] + 1)
        gained_money = random.randint(200, 1000)
        await update_stats(message.from_user.id, add_balance=gained_money, add_subs=gained_subs)
        msg = f"🔥 **ХАЙП УДАЛСЯ!** Ты выложил разоблачение и все об этом говорят!\n➕ **+{gained_subs} подписчиков**\n➕ **+${gained_money}**"
    else:
        await update_stats(message.from_user.id, add_strikes=1)
        msg = f"🚨 **ПРОВАЛ!** На тебя подали в суд за клевету!\n⚠️ Ты получил **+1 Страйк** (Всего: {user['strikes'] + 1}/3)!"
        
    await message.answer(msg, parse_mode="Markdown")

@dp.message(F.text == "🔴 Начать стрим")
async def stream_cmd(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=cat, callback_data=f"stream_{cat}")] for cat in CATEGORIES
    ])
    await message.answer("🎥 Выберите тематику для проведения стрима:", reply_markup=kb)

@dp.callback_query(F.data.startswith("stream_"))
async def process_stream(callback: types.CallbackQuery):
    cat = callback.data.split("stream_")[1]
    user = await get_user(callback.from_user.id)
    trend = get_daily_trend()
    
    trend_mult = 2 if (cat == trend) else 1
    reward = random.randint(40, 200) * (user["rebirths"] + 1) * trend_mult
    subs = random.randint(10, 40) * trend_mult
    
    await update_stats(callback.from_user.id, add_balance=reward, add_subs=subs)
    
    msg = f"🔴 **Стрим по {cat} завершён!**\n"
    if cat == trend:
        msg += f"🔥 **ПОПАЛ В ТРЕНД (x2)!**\n"
    msg += f"➕ Заработано: **+${reward}** | 👥 **+{subs} подп.**"
    await callback.message.edit_text(msg, parse_mode="Markdown")

@dp.message(F.text == "🎬 Записать видео")
async def video_cmd(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=cat, callback_data=f"video_{cat}")] for cat in CATEGORIES
    ])
    await message.answer("🎬 Выберите тематику для нового видео:", reply_markup=kb)

@dp.callback_query(F.data.startswith("video_"))
async def process_video(callback: types.CallbackQuery):
    cat = callback.data.split("video_")[1]
    user = await get_user(callback.from_user.id)
    trend = get_daily_trend()
    
    editor_mult = 2 if user["has_editor"] == 1 else 1
    trend_mult = 2 if (cat == trend) else 1
    
    subs = random.randint(15, 60) * trend_mult
    money = random.randint(20, 120) * (user["rebirths"] + 1) * trend_mult * editor_mult
    
    await update_stats(callback.from_user.id, add_balance=money, add_subs=subs)
    
    msg = f"🎬 **Видео по {cat} опубликовано!**\n"
    if cat == trend:
        msg += f"🔥 **ТРЕНД ДНЯ (x2)!**\n"
    if user["has_editor"] == 1:
        msg += f"🎬 **Монтажёр сделал пушку (x2 к монетизации)!**\n"
    msg += f"📈 Прибыль: **+${money}** | 👥 **+{subs} подп.**"
    await callback.message.edit_text(msg, parse_mode="Markdown")

@dp.message(F.text == "🎁 Посылка")
async def case_cmd(message: types.Message):
    success, msg = await open_daily_case(message.from_user.id)
    await message.answer(msg, parse_mode="Markdown")

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
        "Сбрасывает баланс, покупки и страйки, но дает **постоянный множитель дохода**!\n\n"
        "📌 **Требования:**\n"
        "• Куплены все улучшения (Этап 5)\n"
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
        await message.answer("🎉 Вы купили все доступные улучшения! Доступно **Перерождение**!")

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
