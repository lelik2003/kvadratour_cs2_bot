from aiogram import Router, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from main import api_client

router = Router()

@router.message(CommandStart())
async def cmd_start(message: types.Message):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    username = message.from_user.username or 'Игрок'
    
    # Проверяем привязку
    try:
        site_user = await api_client.get_user_by_telegram(user_id)
    except Exception as e:
        site_user = None
        await message.answer(f"⚠️ Ошибка при проверке аккаунта: {e}")
    
    text = f"""
🎯 <b>Привет, {username}!</b>

Я — <b>CS2 Tournament Bot</b>, твой помощник в мире киберспорта!
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Турниры", callback_data="tournaments")],
        [InlineKeyboardButton(text="👤 Мой профиль", callback_data="profile")],
        [InlineKeyboardButton(text="🔗 Привязать аккаунт", callback_data="link")] if not site_user else [],
        [InlineKeyboardButton(text="❓ Помощь", callback_data="help")]
    ])
    
    if site_user:
        text += f"""
✅ <b>Аккаунт привязан!</b>
👤 Ник: {site_user.get('nickname', 'Неизвестно')}
🏆 Статус: {'Администратор' if site_user.get('is_admin') else 'Игрок'}
"""
    else:
        text += """
⚠️ <b>Аккаунт не привязан!</b>
Нажми кнопку ниже, чтобы привязать аккаунт к сайту.

🔗 <b>Как привязать:</b>
1. Войди в профиль на сайте
2. Нажми "Привязать Telegram"
3. Введи код или нажми кнопку в боте
"""
    
    await message.answer(text, reply_markup=keyboard)
