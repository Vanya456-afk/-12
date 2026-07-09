import aiosqlite
import time

DB_NAME = "tycoon.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                balance REAL DEFAULT 0,
                income_per_sec REAL DEFAULT 1,
                last_collect INTEGER,
                stage INTEGER DEFAULT 1
            )
        ''')
        await db.commit()

async def get_user(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT balance, income_per_sec, last_collect, stage FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                now = int(time.time())
                await db.execute("INSERT INTO users (user_id, balance, income_per_sec, last_collect, stage) VALUES (?, 0, 1, ?, 1)", (user_id, now))
                await db.commit()
                return {"balance": 0, "income_per_sec": 1, "last_collect": now, "stage": 1}
            return {"balance": row[0], "income_per_sec": row[1], "last_collect": row[2], "stage": row[3]}

async def collect_money(user_id: int):
    user = await get_user(user_id)
    now = int(time.time())
    seconds_passed = now - user["last_collect"]
    earned = seconds_passed * user["income_per_sec"]
    
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
