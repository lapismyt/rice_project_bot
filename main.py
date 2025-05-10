from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import html
from dotenv import load_dotenv
import os
import asyncio
import aiosqlite
from datetime import datetime, timedelta
import random
from loguru import logger
# import pymorphy2

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
OWNER_ID = int(os.getenv('OWNER_ID'))
FORMAT = '%Y-%m-%d %H:%M:%S'
ZERO_DATE = datetime(1950, 1, 1, 0, 0, 0, 0)

# morph = pymorphy2.MorphAnalyzer(lang='ru')
bot = Bot(BOT_TOKEN)
dp = Dispatcher()


# def get_plural_form(number: int, word: str) -> str:
#     parsed_word = morph.parse(word)[0]
#     form = parsed_word.inflect({'plur', 'gent'})\
#         if (number % 10 in [2, 3, 4]
#             and number % 100 not in [12, 13, 14])\
#         else parsed_word.inflect({'sing', 'nomn'})
#     return form.word

# def format_timedelta_plural(td: timedelta) -> str:
#     days = td.days
#     seconds = td.seconds
#     hours = seconds // 3600
#     seconds %= 3600
#     minutes = seconds // 60
#
#     parts = []
#     if days > 0:
#         parts.append(f"{days} {get_plural_form(days, 'день')}")
#     if hours > 0:
#         parts.append(f"{hours} {get_plural_form(hours, 'час')}")
#     if minutes > 0:
#         parts.append(f"{minutes} {get_plural_form(minutes, 'минута')}")
#
#     if not parts:
#         return "через минуту"
#     elif len(parts) == 1:
#         return f"через {parts[0]}"
#     else:
#         return f"через {' '.join(parts)}"


def format_timedelta(td: timedelta) -> str:
    days = td.days
    seconds = td.seconds

    hours = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60

    parts = []

    if days > 0:
        parts.append(f"{days} дней")
    if hours > 0:
        parts.append(f"{hours} часов")
    if minutes > 0:
        parts.append(f"{minutes} минут")

    if not parts:
        return "через"
    elif len(parts) == 1:
        return f"через {parts[0]}"
    else:
        return f"через {' '.join(parts)}"


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


async def update_rice(user_id: int) -> dict:
    async with aiosqlite.connect('db.sqlite3') as db:
        async with db.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)) as cur:
            result = await cur.fetchone()
            if result is not None:
                _, rice, last_update = result
                last_update = datetime.strptime(last_update, FORMAT)
                if (last_update + timedelta(days=1)) >= datetime.now():
                    deadline = last_update + timedelta(days=1)
                    return {'rice': rice, 'remaining': deadline - datetime.now()}
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
    return {'rice': rice, 'given': given}


@dp.message(Command('rice'))
async def rice_handler(message: Message):
    data = await update_rice(message.from_user.id)
    rice = data['rice']
    if not 'given' in data:
        when_next = format_timedelta(data['remaining'])
        return await message.reply(f'{message.from_user.full_name}, рис на сегодня закончился, приходи {when_next}.')
    given = data['given']
    if data['given'] > 0:
        return await message.reply(f'{message.from_user.full_name}, ты получил(а) {given} риса. Получено всего - {rice}.')
    if data['given'] < 0:
        return await message.reply(f'{message.from_user.full_name}, у тебя забрали {-given} риса. Получено всего - {rice}.')
    if data['given'] == 0:
        return await message.reply(f'{message.from_user.full_name}, ты получил(а) ничего. Получено всего - {rice}.')
    return None


@dp.message(Command('top'))
async def rice_top(message: Message):
    async with aiosqlite.connect('db.sqlite3') as db:
        async with db.execute('SELECT user_id, rice FROM users ORDER BY rice DESC LIMIT 50') as cur:
            result = await cur.fetchall()
            mess = ''
            for user_idx, user in enumerate(result, start=1):
                # user_member = await bot.get_chat_member(message.chat.id, user[0])
                user_chat = await bot.get_chat(user[0])
                mess += f'{user_idx}. <a href="tg://openmessage?user_id={user[0]}">{html.escape(user_chat.full_name)}</a> - {user[1]}.\n'
    msg = await message.reply(f'Топ по рису:\n{mess}', parse_mode='html')
    await asyncio.sleep(600)
    await msg.delete()
    await message.delete()


async def main():
    await prepare_database()
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
