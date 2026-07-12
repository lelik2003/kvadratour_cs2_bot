from aiogram import Router, types
from aiogram.filters import Command
from config import Config

router = Router()  # <-- СОЗДАЕМ РОУТЕР

@router.message(Command("admin"))
async def cmd_admin(message: types.Message):
    """Админ-панель (только для админов)"""
    user_id = message.from_user.id
    
    if user_id not in Config.ADMIN_IDS:
        await message.answer("❌ У тебя нет доступа к админ-панели")
        return
    
    text = """
🛡️ <b>Админ-панель</b>

Доступные команды:
• <code>/stats</code> — Статистика бота
• <code>/broadcast</code> — Рассылка сообщений
• <code>/check_user</code> — Проверить пользователя
"""
    await message.answer(text)
