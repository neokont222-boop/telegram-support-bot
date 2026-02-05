import os
import asyncio
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage

# ================= ENV =================
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
MASTER_CHAT_ID = int(os.getenv("MASTER_CHAT_ID"))

BOT_NAME = "Тех підтримка Подільський Фермер"

bot = Bot(BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ================= FSM =================
class TicketFSM(StatesGroup):
    shop = State()
    problem = State()
    subproblem = State()
    critical = State()
    description = State()
    media = State()

# ================= КНОПКИ =================

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
        keyboard=[
            [KeyboardButton(text="➡️ Наступний крок")]
        ],
        resize_keyboard=True
    )

def contact_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📞 Поділитись номером", request_contact=True)]
        ],
        resize_keyboard=True
    )

# ================= ЧЕКЛІСТИ =================

CHECKLIST = {
    "Холодильна вітрина":
        "📋 Потрібно надіслати:\n"
        "• Опис поломки\n"
        "• Фото шильдіка\n"
        "• Фото термоконтролера",

    "Холодильний регал":
        "📋 Потрібно надіслати:\n"
        "• Фото термоконтролера\n"
        "• Фото шильдіка\n"
        "• Опис",

    "Морозилка":
        "📋 Потрібно надіслати:\n"
        "• Фото шильдіка\n"
        "• Фото термоконтролера\n"
        "• Опис",

    "Холодильна шафа":
        "📋 Потрібно надіслати:\n"
        "• Фото термоконтролера\n"
        "• Фото шильдіка\n"
        "• Опис",

    "Установка виносного холоду":
        "📋 Потрібно надіслати:\n"
        "• Відео роботи установки\n"
        "• Фото лічильника\n"
        "• Опис",

    "Світло": "📋 Фото проблеми + коментар",
    "Розетка": "📋 Фото проблеми + коментар",
    "Щиток": "📋 Фото проблеми + коментар",
    "Генератор": "📋 Фото генератора + відео запуску + опис",
    "Сантехніка": "📋 Фото + коментар",
    "Двері": "📋 Фото + коментар",
}

# ================= START =================
@dp.message(Command("start"))
async def start(message: Message, state: FSMContext):
    await state.clear()

    await message.answer(
        f"👋 Доброго дня!\n"
        f"Вас вітає {BOT_NAME}.\n"
        "Я створений щоб вирішувати ваші проблеми.\n\n"
        "🏪 Вкажіть найменування магазину:"
    )

    await state.set_state(TicketFSM.shop)

# ================= SHOP =================
@dp.message(TicketFSM.shop)
async def shop(message: Message, state: FSMContext):
    await state.update_data(shop=message.text)

    await message.answer(
        "Оберіть тип проблеми:",
        reply_markup=problem_menu()
    )

    await state.set_state(TicketFSM.problem)

# ================= PROBLEM =================
@dp.message(TicketFSM.problem)
async def problem(message: Message, state: FSMContext):

    await state.update_data(problem=message.text)

    if message.text == "❄️ Холодильне обладнання":
        await message.answer("Оберіть тип:", reply_markup=fridge_menu())

    elif message.text == "⚡ Електрика":
        await message.answer("Оберіть тип:", reply_markup=electric_menu())

    elif message.text == "🔌 Генератор":
        await state.update_data(subproblem="Генератор")
        await message.answer(CHECKLIST["Генератор"])

        await message.answer("Оберіть критичність:", reply_markup=critical_menu())
        await state.set_state(TicketFSM.critical)
        return

    elif message.text == "🚿 Сантехніка":
        await state.update_data(subproblem="Сантехніка")
        await message.answer(CHECKLIST["Сантехніка"])
        await message.answer("Оберіть критичність:", reply_markup=critical_menu())
        await state.set_state(TicketFSM.critical)
        return

    elif message.text == "🚪 Двері":
        await state.update_data(subproblem="Двері")
        await message.answer(CHECKLIST["Двері"])
        await message.answer("Оберіть критичність:", reply_markup=critical_menu())
        await state.set_state(TicketFSM.critical)
        return

    await state.set_state(TicketFSM.subproblem)

# ================= SUBPROBLEM =================
@dp.message(TicketFSM.subproblem)
async def subproblem(message: Message, state: FSMContext):

    await state.update_data(subproblem=message.text)

    if message.text in CHECKLIST:
        await message.answer(CHECKLIST[message.text])

    await message.answer("Оберіть критичність:", reply_markup=critical_menu())
    await state.set_state(TicketFSM.critical)

# ================= CRITICAL =================
@dp.message(TicketFSM.critical)
async def critical(message: Message, state: FSMContext):

    await state.update_data(critical=message.text)

    await message.answer("✏️ Опишіть проблему:")
    await state.set_state(TicketFSM.description)

# ================= DESCRIPTION =================
@dp.message(TicketFSM.description)
async def description(message: Message, state: FSMContext):

    await state.update_data(description=message.text, media=[])

    await message.answer(
        "📸 Завантажте фото або відео.\n"
        "Після завершення натисніть «Наступний крок»",
        reply_markup=media_menu()
    )

    await state.set_state(TicketFSM.media)

# ================= MEDIA =================
@dp.message(TicketFSM.media, F.photo | F.video)
async def media(message: Message, state: FSMContext):

    data = await state.get_data()
    media = data["media"]

    if message.photo:
        media.append(("photo", message.photo[-1].file_id))
    elif message.video:
        media.append(("video", message.video.file_id))

    await state.update_data(media=media)

# ================= NEXT =================
@dp.message(TicketFSM.media, F.text == "➡️ Наступний крок")
async def next_step(message: Message, state: FSMContext):

    data = await state.get_data()

    if not data["media"]:
        await message.answer("❌ Додайте хоча б одне фото або відео")
        return

    await message.answer("Поділіться номером телефону:", reply_markup=contact_menu())

# ================= CONTACT =================
@dp.message(F.contact)
async def contact(message: Message, state: FSMContext):

    data = await state.get_data()
    phone = message.contact.phone_number

    user_link = f'<a href="tg://user?id={message.from_user.id}">{message.from_user.full_name}</a>'

    text = (
        "🛠 <b>НОВИЙ ТІКЕТ</b>\n\n"
        f"🏪 Магазин: {data['shop']}\n"
        f"📂 Проблема: {data['problem']} → {data.get('subproblem','')}\n"
        f"⚠️ Критичність: {data['critical']}\n"
        f"📝 Опис:\n{data['description']}\n\n"
        f"📞 Контакт: {phone}\n"
        f"👤 Автор: {user_link}"
    )

    await bot.send_message(MASTER_CHAT_ID, text, parse_mode="HTML")

    for t, fid in data["media"]:
        if t == "photo":
            await bot.send_photo(MASTER_CHAT_ID, fid)
        else:
            await bot.send_video(MASTER_CHAT_ID, fid)

    await message.answer(
        f"✅ Тікет створено!\n\n"
        f"{BOT_NAME} готовий прийняти нову заявку."
    )

    await message.answer("Вкажіть найменування магазину:")
    await state.set_state(TicketFSM.shop)

# ================= RUN =================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
