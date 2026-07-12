from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu(user_linked: bool = False) -> InlineKeyboardMarkup:
    """Главное меню"""
    buttons = [
        [InlineKeyboardButton(text="🏆 Турниры", callback_data="tournaments")],
        [InlineKeyboardButton(text="👤 Мой профиль", callback_data="profile")],
        [InlineKeyboardButton(text="📊 Матчи", callback_data="matches")],
    ]
    
    if not user_linked:
        buttons.append([InlineKeyboardButton(text="🔗 Привязать аккаунт", callback_data="link")])
    
    buttons.append([InlineKeyboardButton(text="❓ Помощь", callback_data="help")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)
