import logging
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
import os
BOT_TOKEN = os.getenv("BOT_TOKEN")

import nest_asyncio
import asyncio

# Включаем логирование
logging.basicConfig(level=logging.INFO)

# Создаем и подключаемся к базе данных
def create_db():
    conn = sqlite3.connect('tasks.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_name TEXT NOT NULL,
            deadline TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

create_db()

# Состояния FSM
class AddTask(StatesGroup):
    waiting_for_task_name = State()
    waiting_for_deadline = State()

# Инициализация бота и диспетчера с FSM
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Привет! Я бот-напоминалка о дедлайнах.\n\n"
        "Используй /add чтобы добавить задачу, /list — посмотреть дедлайны."
    )

# /add — запуск FSM
@dp.message(Command("add"))
async def cmd_add(message: types.Message, state: FSMContext):
    await message.answer("Введите название задачи:")
    await state.set_state(AddTask.waiting_for_task_name)

# Шаг 1 — название задачи
@dp.message(AddTask.waiting_for_task_name)
async def get_task_name(message: types.Message, state: FSMContext):
    await state.update_data(task_name=message.text)
    await message.answer("Введите дедлайн для задачи (формат: YYYY-MM-DD):")
    await state.set_state(AddTask.waiting_for_deadline)

# Шаг 2 — дедлайн и сохранение
@dp.message(AddTask.waiting_for_deadline)
async def get_deadline(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    task_name = user_data["task_name"]
    deadline = message.text

    # Сохраняем в БД
    conn = sqlite3.connect('tasks.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tasks (task_name, deadline) VALUES (?, ?)", (task_name, deadline))
    conn.commit()
    conn.close()

    await message.answer(f"✅ Задача <b>{task_name}</b> добавлена с дедлайном <b>{deadline}</b>.")
    await state.clear()

# /list
@dp.message(Command("list"))
async def cmd_list(message: types.Message):
    conn = sqlite3.connect('tasks.db')
    cursor = conn.cursor()
    cursor.execute("SELECT task_name, deadline FROM tasks")
    tasks = cursor.fetchall()
    conn.close()

    if tasks:
        tasks_list = "\n".join([f"📌 <b>{task[0]}</b> — до <i>{task[1]}</i>" for task in tasks])
        await message.answer(f"<b>Список задач:</b>\n{tasks_list}")
    else:
        await message.answer("🙌 Нет задач в базе данных.")

# Запуск бота
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

# Для работы с уже запущенным event loop в Spyder
if __name__ == "__main__":
    nest_asyncio.apply()  # Применяем patch для работы с event loop
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

