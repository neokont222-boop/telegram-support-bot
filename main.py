import os
import asyncio
from typing import Set
from dotenv import load_dotenv
from openpyxl import Workbook

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, KeyboardButton, ReplyKeyboardMarkup,
    InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
)
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage

from db import (
    init_db,
    create_ticket,
    update_ticket_status,
    get_all_tickets,
    get_tickets_by_status
)

# ================= ENV =================
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
MASTER_CHAT_ID = int(os.getenv("MASTER_CHAT_ID"))
BOT_NAME = "Тех підтримка Подільський Фермер"

ADMIN_IDS: Set[int] = set(
    int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()
)

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

bot = Bot(BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ================= AUTHOR =================
def format_author(user):
    if user.username:
        return f'<a href="https://t.me/{user.username}">@{user.username}</a>'
    return f'<a href="tg://user?id={user.id}">{user.full_name}</a>'

# ================= FSM =================
class TicketFSM(StatesGroup):
    shop = State()
    problem = State()
    subproblem = State()
    critical = State()
    description = State()
    media = State()

# ================= BUTTONS =================
def problem_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="❄️ Холодильне обладнання")],
            [KeyboardButton(text="⚡ Електрика")],
            [KeyboardButton(text="🔌 Генератор")],
            [KeyboardButton(text="🚿 Сантехніка")],
            [KeyboardButton(text="🚪 Двері")]
        ],
        resize_keyboard=True
    )

def fridge_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Холодильна вітрина")],
            [KeyboardButton(text="Холодильний регал")],
            [KeyboardButton(text="Морозилка")],
            [KeyboardButton(text="Холодильна шафа")],
            [KeyboardButton(text="Установка виносного холоду")]
        ],
        resize_keyboard=True
    )

def electric_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Світло")],
            [KeyboardButton(text="Розетка")],
            [KeyboardButton(text="Щиток")]
        ],
        resize_keyboard=True
    )

def critical_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔴 Терміново")],
            [KeyboardButton(text="🟡 Планово")]
        ],
        resize_keyboard=True
    )

def media_menu():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="➡️ Наступний крок")]],
        resize_keyboard=True
    )

def contact_menu():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📞 Поділитись номером", request_contact=True)]],
        resize_keyboard=True
    )

def status_keyboard(ticket_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔧 В роботі", callback_data=f"status:in_work:{ticket_id}"),
            InlineKeyboardButton(text="✅ Виконано", callback_data=f"status:done:{ticket_id}")
        ],
        [
            InlineKeyboardButton(text="❌ Скасовано", callback_data=f"status:canceled:{ticket_id}")
        ]
    ])

def admin_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Всі заявки", callback_data="admin:all")],
        [
            InlineKeyboardButton(text="🔧 В роботі", callback_data="admin:in_work"),
            InlineKeyboardButton(text="✅ Виконані", callback_data="admin:done")
        ],
        [InlineKeyboardButton(text="❌ Скасовані", callback_data="admin:canceled")],
        [InlineKeyboardButton(text="📊 Експорт Excel", callback_data="admin:export")]
    ])

# ================= CONST =================
CHECKLIST = {
    "Холодильна вітрина": "📋 Опис + фото шильдіка + фото термоконтролера",
    "Холодильний регал": "📋 Фото термоконтролера + фото шильдіка + опис",
    "Морозилка": "📋 Фото шильдіка + фото термоконтролера + опис",
    "Холодильна шафа": "📋 Фото термоконтролера + фото шильдіка + опис",
    "Установка виносного холоду": "📋 Відео роботи + фото лічильника + опис",
    "Світло": "📋 Фото + коментар",
    "Розетка": "📋 Фото + коментар",
    "Щиток": "📋 Фото + коментар",
    "Генератор": "📋 Фото генератора + відео запуску + опис",
    "Сантехніка": "📋 Фото + коментар",
    "Двері": "📋 Фото + коментар",
}

STATUS_LABELS = {
    "new": "🆕 Нова",
    "in_work": "🔧 В роботі",
    "done": "✅ Виконано",
    "canceled": "❌ Скасовано"
}

# ================= START =================
@dp.message(Command("start"))
async def start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        f"👋 Доброго дня!\nВас вітає {BOT_NAME}.\n\n🏪 Вкажіть найменування магазину:"
    )
    await state.set_state(TicketFSM.shop)

# ================= FLOW =================
@dp.message(TicketFSM.shop)
async def shop(message: Message, state: FSMContext):
    await state.update_data(shop=message.text)
    await message.answer("Оберіть тип проблеми:", reply_markup=problem_menu())
    await state.set_state(TicketFSM.problem)

@dp.message(TicketFSM.problem)
async def problem(message: Message, state: FSMContext):
    await state.update_data(problem=message.text)

    if message.text == "❄️ Холодильне обладнання":
        await message.answer("Оберіть тип:", reply_markup=fridge_menu())
        await state.set_state(TicketFSM.subproblem)
        return

    if message.text == "⚡ Електрика":
        await message.answer("Оберіть тип:", reply_markup=electric_menu())
        await state.set_state(TicketFSM.subproblem)
        return

    sub = message.text.replace("🔌 ", "").replace("🚿 ", "").replace("🚪 ", "")
    await state.update_data(subproblem=sub)

    await message.answer(CHECKLIST[sub])
    await message.answer("Оберіть критичність:", reply_markup=critical_menu())
    await state.set_state(TicketFSM.critical)

@dp.message(TicketFSM.subproblem)
async def subproblem(message: Message, state: FSMContext):
    await state.update_data(subproblem=message.text)
    await message.answer(CHECKLIST.get(message.text, ""))
    await message.answer("Оберіть критичність:", reply_markup=critical_menu())
    await state.set_state(TicketFSM.critical)

@dp.message(TicketFSM.critical)
async def critical(message: Message, state: FSMContext):
    await state.update_data(critical=message.text)
    await message.answer("✏️ Опишіть проблему:")
    await state.set_state(TicketFSM.description)

@dp.message(TicketFSM.description)
async def description(message: Message, state: FSMContext):
    await state.update_data(description=message.text, media=[])
    await message.answer("📸 Надішліть фото або відео\nПісля — «Наступний крок»", reply_markup=media_menu())
    await state.set_state(TicketFSM.media)

@dp.message(TicketFSM.media, F.photo | F.video)
async def media(message: Message, state: FSMContext):
    data = await state.get_data()
    media = data["media"]

    if message.photo:
        media.append(("photo", message.photo[-1].file_id))
    if message.video:
        media.append(("video", message.video.file_id))

    await state.update_data(media=media)

@dp.message(TicketFSM.media, F.text == "➡️ Наступний крок")
async def next_step(message: Message, state: FSMContext):
    data = await state.get_data()
    if not data["media"]:
        await message.answer("❌ Додайте хоча б одне фото або відео")
        return
    await message.answer("Поділіться номером телефону:", reply_markup=contact_menu())

@dp.message(F.contact)
async def contact(message: Message, state: FSMContext):
    data = await state.get_data()
    phone = message.contact.phone_number
    author = format_author(message.from_user)

    ticket_id = create_ticket(
        shop=data["shop"],
        problem=data["problem"],
        subproblem=data.get("subproblem", ""),
        critical=data["critical"],
        description=data["description"],
        phone=phone,
        author_id=message.from_user.id,
        author_name=message.from_user.full_name
    )

    text = (
        f"🛠 <b>НОВИЙ ТІКЕТ #{ticket_id}</b>\n\n"
        f"🏪 Магазин: {data['shop']}\n"
        f"📂 Проблема: {data['problem']} → {data.get('subproblem','')}\n"
        f"⚠️ Критичність: {data['critical']}\n"
        f"📝 Опис:\n{data['description']}\n\n"
        f"📞 Контакт: {phone}\n"
        f"👤 Автор: {author}"
    )

    await bot.send_message(MASTER_CHAT_ID, text, parse_mode="HTML")

    for t, fid in data["media"]:
        await (bot.send_photo if t == "photo" else bot.send_video)(MASTER_CHAT_ID, fid)

    await bot.send_message(
        MASTER_CHAT_ID,
        f"🔘 Управління заявкою #{ticket_id}:",
        reply_markup=status_keyboard(ticket_id)
    )

    await message.answer("✅ Тікет створено!\n\nМожна створювати нову заявку.")
    await message.answer("🏪 Вкажіть найменування магазину:")
    await state.set_state(TicketFSM.shop)

# ================= STATUS =================
@dp.callback_query(F.data.startswith("status:"))
async def change_status(call: CallbackQuery):
    _, status, ticket_id = call.data.split(":")
    update_ticket_status(int(ticket_id), status)
    await call.message.answer(f"🔄 Статус заявки #{ticket_id} змінено на {STATUS_LABELS[status]}")
    await call.answer("Готово")

# ================= ADMIN =================
@dp.message(Command("admin"))
async def admin_start(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ заборонено")
        return
    await message.answer("👮‍♂️ Адмін-меню:", reply_markup=admin_menu())

@dp.callback_query(F.data.startswith("admin:"))
async def admin_actions(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("⛔", show_alert=True)
        return

    action = call.data.split(":")[1]

    if action == "export":
        await export_excel(call.message)
        await call.answer()
        return

    status = None if action == "all" else action
    tickets = get_tickets_by_status(status)

    if not tickets:
        await call.message.answer("Немає заявок")
        await call.answer()
        return

    text = "📋 <b>Заявки</b>\n\n"
    for t in tickets[:30]:
        text += (
            f"#{t[0]} | {t[1]}\n"
            f"{t[2]} → {t[3]}\n"
            f"{STATUS_LABELS[t[5]]}\n"
            f"🕒 {t[6][:16]}\n\n"
        )

    await call.message.answer(text, parse_mode="HTML")
    await call.answer()

# ================= EXPORT =================
async def export_excel(message: Message):
    tickets = get_all_tickets()

    wb = Workbook()
    ws = wb.active
    ws.append(["ID", "Магазин", "Проблема", "Підтип", "Критичність", "Статус", "Дата"])

    for t in tickets:
        ws.append(t)

    file = "tickets.xlsx"
    wb.save(file)
    await message.answer_document(open(file, "rb"), caption="📊 Excel")

# ================= RUN =================
async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
