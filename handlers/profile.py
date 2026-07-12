from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from api_client import APIClient  # <-- ТОЛЬКО ЭТОТ ИМПОРТ!

router = Router()
api = APIClient()  # <-- СОЗДАЕМ ЭКЗЕМПЛЯР ЗДЕСЬ

@router.message(Command("profile"))
async def cmd_profile(message: types.Message):
    """Показать профиль пользователя"""
    user_id = message.from_user.id
    
    site_user = await api.get_user_by_telegram(user_id)
    
    if not site_user:
        text = """
⚠️ <b>Аккаунт не привязан!</b>
Нажми кнопку ниже 👇
"""
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Привязать аккаунт", callback_data="link")]
        ])
        await message.answer(text, reply_markup=keyboard)
        return
    
    stats = site_user.get('stats', {})
    nickname = site_user.get('nickname', 'Игрок')
    elo = stats.get('elo', 1000)
    wins = stats.get('wins', 0)
    losses = stats.get('losses', 0)
    total_matches = wins + losses
    winrate = round((wins / total_matches * 100), 1) if total_matches > 0 else 0
    kd = stats.get('kd', 0)
    
    text = f"""
👤 <b>Профиль игрока</b>

<b>Ник:</b> {nickname}
<b>SteamID:</b> {site_user.get('steamid', 'Неизвестно')}

📊 <b>Статистика:</b>
• Рейтинг (ELO): <b>{elo}</b>
• Матчи: <b>{total_matches}</b> ({wins} побед, {losses} поражений)
• Винрейт: <b>{winrate}%</b>
• K/D: <b>{kd}</b>

💰 <b>Баланс:</b> {site_user.get('balance', 0)} ₽
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Полная статистика", callback_data="full_stats")],
        [InlineKeyboardButton(text="🔓 Отвязать аккаунт", callback_data="unlink")]
    ])
    
    await message.answer(text, reply_markup=keyboard)

@router.callback_query(lambda c: c.data == "profile")
async def callback_profile(callback: types.CallbackQuery):
    await callback.answer()
    await cmd_profile(callback.message)

@router.callback_query(lambda c: c.data == "link")
async def callback_link(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        "🔗 Привязка аккаунта\n\n"
        "1️⃣ Перейди на сайт и войди в профиль\n"
        "2️⃣ Нажми кнопку 'Привязать Telegram'\n"
        "3️⃣ Введи код, который придет в ответе\n\n"
        "Или введи свой ID с сайта: <code>/link 123</code>"
    )
