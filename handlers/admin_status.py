from aiogram import Router, F
from aiogram.types import CallbackQuery

from db import update_ticket_status_with_admin
from main import is_admin, STATUS_LABELS

router = Router()


@router.callback_query(F.data.startswith("status:"))
async def change_status(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("⛔ Немає прав", show_alert=True)
        return

    _, status, ticket_id = call.data.split(":")
    ticket_id = int(ticket_id)

    admin_name = (
        f"@{call.from_user.username}"
        if call.from_user.username
        else call.from_user.full_name
    )

    update_ticket_status_with_admin(
        ticket_id=ticket_id,
        status=status,
        admin_name=admin_name
    )

    await call.message.answer(
        f"📄 Заявка №{ticket_id}\n"
        f"🔄 Статус: {STATUS_LABELS.get(status, status)}\n"
        f"👤 Адмін: {admin_name}"
    )

    await call.answer("✅ Статус оновлено")
