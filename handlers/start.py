from aiogram import Router, types
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from main import api

router = Router()

@router.message(CommandStart())
async def cmd_start(message: types.Message):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    username = message.from_user.username or 'Игрок'
    
    # Проверяем, привязан ли аккаунт
    site_user = await api.get_user_by_telegram(user_id)
    
    text = f"""
🎯 <b>Привет, {username}!</b>

Я — <b>CS2 Tournament Bot</b>, твой помощник в мире киберспорта!

"""
    
    if site_user:
        text += f"""
✅ <b>Аккаунт привязан!</b>
👤 Ник: {site_user.get('nickname', 'Неизвестно')}
🏆 Рейтинг: {site_user.get('stats', {}).get('elo', 1000)}
"""
    else:
        text += """
⚠️ <b>Аккаунт не привязан!</b>
Нажми кнопку ниже, чтобы привязать аккаунт к сайту.

🔗 <b>Привязка нужна для:</b>
• Просмотра твоего профиля
• Участия в турнирах
• Получения уведомлений
• Обновления статистики
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Турниры", callback_data="tournaments")],
        [InlineKeyboardButton(text="👤 Мой профиль", callback_data="profile")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton(text="🔗 Привязать аккаунт", callback_data="link")] if not site_user else [],
        [InlineKeyboardButton(text="❓ Помощь", callback_data="help")]
    ])
    
    await message.answer(text, reply_markup=keyboard)