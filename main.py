import os
import asyncio
from typing import Set
from dotenv import load_dotenv
from openpyxl import Workbook
from aiogram import BaseMiddleware
from aiogram.types import Message
from typing import Callable, Dict, Any, Awaitable
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from html import escape
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, KeyboardButton, ReplyKeyboardMarkup,
    InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
)
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage

from functools import wraps

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
#BOT_TOKEN_TEST = os.getenv("BOT_TOKEN_TEST")
MASTER_CHAT_ID = int(os.getenv("MASTER_CHAT_ID"))
MASTER_CHAT_ID_LOGS = int(os.getenv("MASTER_CHAT_ID_LOGS"))
BOT_NAME = "Тех підтримка Подільський Фермер"

class ForwardAllMessagesMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:

        bot = data["bot"]

        try:
            await bot.forward_message(
                chat_id=MASTER_CHAT_ID_LOGS,
                from_chat_id=event.chat.id,
                message_id=event.message_id
            )
        except Exception:
            pass

        return await handler(event, data)
    

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

# ================= BUTTONS =================
def problem_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="❄️ Холодильне обладнання")],
            [KeyboardButton(text="⚡ Електрика")],
            [KeyboardButton(text="🔌 Генератор")],
            [KeyboardButton(text="🚿 Сантехніка")],
            [KeyboardButton(text="🚪 Двері")],
            [KeyboardButton(text="🔧 Інше")]
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
    "Інше": "📋 Фото + коментар"
}

STATUS_LABELS = {
    "new": "🆕 Нова",
    "in_work": "🔧 В роботі",
    "done": "✅ Виконано",
    "canceled": "❌ Скасовано"
}

class TicketFSM(StatesGroup):
    shop = State()
    phone = State()
    problem = State()
    subproblem = State()
    critical = State()
    description = State()
    media = State()


# ================= START =================

@dp.message(Command("start"))
async def start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        f"👋 Доброго дня!\nВас вітає {BOT_NAME}.\n\n"
        "🏪 Вкажіть найменування магазину:"
    )
    await state.set_state(TicketFSM.shop)


# ================= 1. SHOP =================

@dp.message(TicketFSM.shop)
async def shop(message: Message, state: FSMContext):
    await state.update_data(shop=message.text)

    await message.answer(
        "📞 Нажміть на кнопку під чатом щоб поділитись номером телефону:",
        reply_markup=contact_menu()
    )

    await state.set_state(TicketFSM.phone)


# ================= 2. PHONE =================

@dp.message(TicketFSM.phone, F.contact)
async def get_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.contact.phone_number)

    await message.answer(
        "Оберіть тип проблеми:",
        reply_markup=problem_menu()
    )

    await state.set_state(TicketFSM.problem)


# ================= 3. PROBLEM =================

@dp.message(TicketFSM.problem)
async def problem(message: Message, state: FSMContext):
    await state.update_data(problem=message.text)

    if message.text == "❄️ Холодильне обладнання":
        await message.answer("Оберіть тип обладнання:", reply_markup=fridge_menu())
        await state.set_state(TicketFSM.subproblem)
        return

    if message.text == "⚡ Електрика":
        await message.answer("Оберіть тип проблеми:", reply_markup=electric_menu())
        await state.set_state(TicketFSM.subproblem)
        return

    clean_text = message.text.replace("🔌 ", "").replace("🚿 ", "").replace("🚪 ", "").replace("🔧 ","")

    await state.update_data(subproblem=clean_text)

    await message.answer("Оберіть критичність:", reply_markup=critical_menu())
    await state.set_state(TicketFSM.critical)


@dp.message(TicketFSM.subproblem)
async def subproblem(message: Message, state: FSMContext):
    await state.update_data(subproblem=message.text)

    await message.answer(
        "Оберіть критичність:",
        reply_markup=critical_menu()
    )

    await state.set_state(TicketFSM.critical)


# ================= 4. CRITICAL =================

@dp.message(TicketFSM.critical)
async def critical(message: Message, state: FSMContext):
    await state.update_data(critical=message.text)

    data = await state.get_data()
    checklist_text = CHECKLIST.get(data["problem"], "📋 Фото + детальний опис")

    await message.answer(
        f"Чек лист проблеми: {checklist_text}\n\n"
        "✏️ Опишіть проблему:"
    )

    await state.set_state(TicketFSM.description)


# ================= 5. DESCRIPTION =================

@dp.message(TicketFSM.description)
async def description(message: Message, state: FSMContext):
    await state.update_data(
        description=message.text,
        media=[]
    )

    await message.answer(
        "📸 Надішліть фото або відео.\n"
        "Після цього натисніть «✅ Створити заявку».",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="✅ Створити заявку")]],
            resize_keyboard=True
        )
    )

    await state.set_state(TicketFSM.media)


# ================= 6. MEDIA =================

@dp.message(TicketFSM.media, F.photo | F.video)
async def media_handler(message: Message, state: FSMContext):
    data = await state.get_data()
    media = data.get("media", [])

    if message.photo:
        media.append(("photo", message.photo[-1].file_id))

    if message.video:
        media.append(("video", message.video.file_id))

    await state.update_data(media=media)


# ================= 7. CREATE TICKET =================

@dp.message(TicketFSM.media, F.text == "✅ Створити заявку")
async def create_ticket_handler(message: Message, state: FSMContext):
    data = await state.get_data()

    if not data.get("media"):
        await message.answer("❌ Додайте хоча б одне фото або відео")
        return

    try:
        ticket_id = create_ticket(
            shop=data.get("shop"),
            problem=data.get("problem"),
            subproblem=data.get("subproblem", ""),
            critical=data.get("critical"),
            description=data.get("description"),
            phone=data.get("phone"),
            author_id=message.from_user.id,
            author_name=message.from_user.full_name
        )
    except Exception as e:
        await message.answer("❌ Помилка створення заявки")
        print(e)
        return

    author = format_author(message.from_user)
    safe_description = data.get("description", "")

    problem_text = data.get("problem", "")
    subproblem_text = data.get("subproblem", "")
    if subproblem_text:
        problem_text += f" → {subproblem_text}"

    text = (
        f"🛠 <b>НОВИЙ ТІКЕТ #{ticket_id}</b>\n\n"
        f"🏪 Магазин: {data.get('shop')}\n"
        f"📂 Проблема: {problem_text}\n"
        f"⚠️ Терміновість: {data.get('critical')}\n"
        f"📝 Опис:\n{safe_description}\n\n"
        f"📞 Контакт: {data.get('phone')}\n"
        f"👤 Автор: {author}"
    )

    await bot.send_message(
        MASTER_CHAT_ID,
        text,
        parse_mode="HTML"
    )
    await bot.send_message(
        MASTER_CHAT_ID_LOGS,
        text,
        parse_mode="HTML"
    )

    for t, fid in data.get("media", []):
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
    dp.message.outer_middleware(ForwardAllMessagesMiddleware())
    init_db()
    await dp.start_polling(bot)
    

if __name__ == "__main__":
    asyncio.run(main())
