from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from loader import api
from config import Config

router = Router()

@router.message(Command("profile"))
async def cmd_profile(message: types.Message):
    """Показать профиль пользователя"""
    user_id = message.from_user.id
    
    # Проверяем привязку
    site_user = await api.get_user_by_telegram(user_id)
    
    if not site_user:
        text = """
⚠️ <b>Аккаунт не привязан!</b>

Чтобы просмотреть профиль, привяжи аккаунт к сайту.

Нажми кнопку ниже 👇
"""
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Привязать аккаунт", callback_data="link")]
        ])
        await message.answer(text, reply_markup=keyboard)
        return
    
    # Формируем профиль
    stats = site_user.get('stats', {})
    nickname = site_user.get('nickname', 'Игрок')
    elo = stats.get('elo', 1000)
    wins = stats.get('wins', 0)
    losses = stats.get('losses', 0)
    total_matches = wins + losses
    winrate = round((wins / total_matches * 100), 1) if total_matches > 0 else 0
    kd = stats.get('kd', 0)
    kills = stats.get('total_kills', 0)
    deaths = stats.get('total_deaths', 0)
    
    text = f"""
👤 <b>Профиль игрока</b>

<b>Ник:</b> {nickname}
<b>SteamID:</b> {site_user.get('steamid', 'Неизвестно')}

📊 <b>Статистика:</b>
• Рейтинг (ELO): <b>{elo}</b>
• Матчи: <b>{total_matches}</b> ({wins} побед, {losses} поражений)
• Винрейт: <b>{winrate}%</b>
• K/D: <b>{kd}</b>
• Убийства: <b>{kills}</b>
• Смерти: <b>{deaths}</b>

💰 <b>Баланс:</b> {site_user.get('balance', 0)} ₽
"""
    
    if site_user.get('is_premium'):
        text += "\n⭐ <b>Premium</b> активен!"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Полная статистика", callback_data="full_stats")],
        [InlineKeyboardButton(text="🏆 Мои турниры", callback_data="my_tournaments")],
        [InlineKeyboardButton(text="🔓 Отвязать аккаунт", callback_data="unlink")]
    ])
    
    await message.answer(text, reply_markup=keyboard)

@router.callback_query(lambda c: c.data == "profile")
async def callback_profile(callback: types.CallbackQuery):
    await callback.answer()
    await cmd_profile(callback.message)

@router.callback_query(lambda c: c.data == "link")
async def callback_link(callback: types.CallbackQuery):
    """Начать процесс привязки аккаунта"""
    user_id = callback.from_user.id
    
    # Проверяем, не привязан ли уже
    site_user = await api.get_user_by_telegram(user_id)
    if site_user:
        await callback.answer("Аккаунт уже привязан!")
        return
    
    text = """
🔗 <b>Привязка аккаунта</b>

Чтобы привязать аккаунт к сайту:

1️⃣ Перейди на сайт и войди в профиль
2️⃣ Нажми кнопку <b>"Привязать Telegram"</b>
3️⃣ Введи код, который придет в ответе

Или введи свой <b>ID с сайта</b> в формате:
<code>/link 123</code>

Где <b>123</b> — это твой ID на сайте.
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌐 Открыть сайт", url="https://lelik.gamer.gd")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_start")]
    ])
    
    await callback.message.answer(text, reply_markup=keyboard)

@router.message(Command("link"))
async def cmd_link(message: types.Message):
    """Команда /link <id>"""
    user_id = message.from_user.id
    args = message.text.split()
    
    if len(args) < 2:
        await message.answer(
            "❌ Укажи свой ID на сайте.\n"
            "Пример: <code>/link 123</code>"
        )
        return
    
    try:
        site_user_id = int(args[1])
    except ValueError:
        await message.answer("❌ ID должен быть числом")
        return
    
    # Проверяем, не привязан ли уже
    existing = await api.get_user_by_telegram(user_id)
    if existing:
        await message.answer("❌ Твой Telegram уже привязан к другому аккаунту")
        return
    
    # Привязываем
    success = await api.link_user(user_id, site_user_id)
    
    if success:
        await message.answer("✅ Аккаунт успешно привязан! 🎉")
    else:
        await message.answer("❌ Ошибка привязки. Проверь ID и попробуй снова.")
