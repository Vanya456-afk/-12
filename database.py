import aiosqlite
import time
import random

DB_NAME = "tycoon.db"

# Список доступных тематик
CATEGORIES = ["Brawl Stars", "Minecraft", "Horror Games", "IRL (Влоги)", "Летсплеи"]

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT DEFAULT 'Игрок',
                balance REAL DEFAULT 0,
                income_per_sec REAL DEFAULT 1,
                last_collect INTEGER,
                stage INTEGER DEFAULT 1,
                subscribers INTEGER DEFAULT 0,
                rebirths INTEGER DEFAULT 0,
                last_case INTEGER DEFAULT 0
            )
        ''')
        await db.commit()

async def get_user(user_id: int, username: str = "Игрок"):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT balance, income_per_sec, last_collect, stage, subscribers, rebirths, last_case FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            now = int(time.time())
            if not row:
                await db.execute(
                    "INSERT INTO users (user_id, username, balance, income_per_sec, last_collect, stage, subscribers, rebirths, last_case) VALUES (?, ?, 0, 1, ?, 1, 0, 0, 0)",
                    (user_id, username, now)
                )
                await db.commit()
                return {"balance": 0, "income_per_sec": 1, "last_collect": now, "stage": 1, "subscribers": 0, "rebirths": 0, "last_case": 0}
            else:
                await db.execute("UPDATE users SET username = ? WHERE user_id = ?", (username, user_id))
                await db.commit()
            return {"balance": row[0], "income_per_sec": row[1], "last_collect": row[2], "stage": row[3], "subscribers": row[4], "rebirths": row[5], "last_case": row[6]}

async def collect_money(user_id: int):
    user = await get_user(user_id)
    now = int(time.time())
    seconds_passed = now - user["last_collect"]
    multiplier = 1 + (user["rebirths"] * 1.0)
    earned = seconds_passed * user["income_per_sec"] * multiplier
    
    new_balance = user["balance"] + earned
    
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET balance = ?, last_collect = ? WHERE user_id = ?", (new_balance, now, user_id))
        await db.commit()
        
    return earned, new_balance

async def buy_upgrade(user_id: int, cost: float, add_income: float, next_stage: int):
    user = await get_user(user_id)
    if user["balance"] < cost:
        return False, "Недостаточно денег!"
    
    new_balance = user["balance"] - cost
    new_income = user["income_per_sec"] + add_income
    
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET balance = ?, income_per_sec = ?, stage = ? WHERE user_id = ?", 
                         (new_balance, new_income, next_stage, user_id))
        await db.commit()
        
    return True, "Успешно куплено!"

async def update_stats(user_id: int, add_balance: float = 0, add_subs: int = 0):
    user = await get_user(user_id)
    new_balance = user["balance"] + add_balance
    new_subs = user["subscribers"] + add_subs
    
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET balance = ?, subscribers = ? WHERE user_id = ?", (new_balance, new_subs, user_id))
        await db.commit()

async def open_daily_case(user_id: int):
    user = await get_user(user_id)
    now = int(time.time())
    cooldown = 24 * 3600 # 24 часа
    
    if now - user["last_case"] < cooldown:
        remaining = cooldown - (now - user["last_case"])
        hours = remaining // 3600
        minutes = (remaining % 3600) // 60
        return False, f"⏳ Посылка ещё не пришла! Приходи через {hours} ч. {minutes} мин."
    
    # Генерация награды
    loot_type = random.choice(["money", "subs", "golden_button"])
    
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET last_case = ? WHERE user_id = ?", (now, user_id))
        await db.commit()

    if loot_type == "money":
        reward = random.randint(500, 3000) * (user["rebirths"] + 1)
        await update_stats(user_id, add_balance=reward)
        return True, f"📦 Из посылки фанатов выпало: **${reward}** на покупку нового оборудования!"
    elif loot_type == "subs":
        reward_subs = random.randint(100, 500) * (user["rebirths"] + 1)
        await update_stats(user_id, add_subs=reward_subs)
        return True, f"📦 Фанаты запустили о тебе флешмоб! **+{reward_subs} новых подписчиков**!"
    else:
        reward = 5000 * (user["rebirths"] + 1)
        await update_stats(user_id, add_balance=reward, add_subs=300)
        return True, f"🏆 **ЛЕГЕНДАРКА!** В посылке оказалась **Золотая Кнопка YouTube**!\n➕ Получено: **${reward}** и **+300 подписчиков**!"

async def do_rebirth(user_id: int):
    user = await get_user(user_id)
    if user["stage"] < 5 or user["balance"] < 10000:
        return False, "Для перерождения нужно пройти все покупки и иметь $10,000 на балансе!"
    
    new_rebirths = user["rebirths"] + 1
    now = int(time.time())
    
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE users SET balance = 0, income_per_sec = 1, stage = 1, last_collect = ?, rebirths = ? WHERE user_id = ?",
            (now, new_rebirths, user_id)
        )
        await db.commit()
        
    return True, f"🎉 Вы совершили Перерождение #{new_rebirths}! Твой множитель дохода вырос!"

async def get_top_players():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT username, balance, subscribers FROM users ORDER BY balance DESC LIMIT 10") as cursor:
            return await cursor.fetchall()
