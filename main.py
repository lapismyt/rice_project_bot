from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from dotenv import load_dotenv
import os
import asyncio
import aiosqlite
from datetime import datetime, timedelta
import random
from loguru import logger

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
OWNER_ID = int(os.getenv('OWNER_ID'))
FORMAT = '%Y-%m-%d %H:%M:%S'
ZERO_DATE = datetime(1950, 1, 1, 0, 0, 0, 0)

bot = Bot(BOT_TOKEN)
dp = Dispatcher()


async def prepare_database():
    async with aiosqlite.connect('db.sqlite3') as db:
        await db.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            rice INTEGER NOT NULL,
            last_update TEXT NOT NULL
        )
        ''')
        await db.commit()


async def update_rice(user_id: int) -> None | tuple[int, int]:
    async with aiosqlite.connect('db.sqlite3') as db:
        async with db.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)) as cur:
            result = await cur.fetchone()
            if result is not None:
                _, rice, last_update = result
                last_update = datetime.strptime(last_update, FORMAT)
                if (last_update + timedelta(days=1)) >= datetime.now():
                    return None
            else:
                rice = 0
        last_update = datetime.now()
        given = random.randint(-5, 10)
        rice += given
        await db.execute('INSERT INTO users (user_id, rice, last_update) '
                         'VALUES (?, ?, ?) ON CONFLICT(user_id) DO UPDATE SET '
                         'rice = excluded.rice, last_update = excluded.last_update',
                         (user_id, rice, last_update.strftime(FORMAT)))
        await db.commit()
    return rice, given


@dp.message(Command('rice'))
async def rice_handler(message: Message):
    res = await update_rice(message.from_user.id)
    if res is None:
        return await message.reply('занято, завтра приходи')
    rice, given = res
    if given > 0:
        return await message.reply(f'поздравляю, ты получил {given}, теперь у тебя {rice}')
    if given < 0:
        return await message.reply(f'у тебя забрали {-given}, теперь у тебя {rice}')
    return None


async def main():
    await prepare_database()
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
