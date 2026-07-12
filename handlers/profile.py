from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from main import api_client

router = Router()

@router.message(Command("profile"))
async def cmd_profile(message: types.Message):
    """Показать профиль пользователя"""
    user_id = message.from_user.id
    
    try:
        site_user = await api_client.get_user_by_telegram(user_id)
    except Exception as e:
        await message.answer(f"⚠️ Ошибка получения профиля: {e}")
        return
    
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
    
    nickname = site_user.get('nickname', 'Игрок')
    is_admin = site_user.get('is_admin', False)
    admin_level = site_user.get('admin_level', 0)
    balance = site_user.get('balance', 0)
    steamid = site_user.get('steamid', 'Неизвестно')
    
    text = f"""
👤 <b>Профиль игрока</b>

<b>Ник:</b> {nickname}
<b>SteamID:</b> {steamid}
<b>Баланс:</b> {balance} ₽
<b>Статус:</b> {'👑 Администратор' if is_admin else '🎮 Игрок'}
"""
    
    if is_admin:
        text += f"<b>Уровень админа:</b> {admin_level}\n"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌐 Открыть профиль на сайте", url="https://lelik.gamer.gd")],
        [InlineKeyboardButton(text="🔓 Отвязать аккаунт", callback_data="unlink")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_start")]
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
    try:
        site_user = await api_client.get_user_by_telegram(user_id)
    except Exception:
        site_user = None
    
    if site_user:
        await callback.answer("✅ Аккаунт уже привязан!")
        return
    
    text = """
🔗 <b>Привязка аккаунта</b>

Чтобы привязать аккаунт к сайту:

1️⃣ Перейди на сайт и войди в профиль
2️⃣ Нажми кнопку <b>"Привязать Telegram"</b>
3️⃣ Введи код, который придет в боте

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
    try:
        existing = await api_client.get_user_by_telegram(user_id)
    except Exception:
        existing = None
    
    if existing:
        await message.answer("❌ Твой Telegram уже привязан к другому аккаунту")
        return
    
    # Привязываем
    try:
        success = await api_client.link_user(user_id, site_user_id)
    except Exception as e:
        await message.answer(f"❌ Ошибка привязки: {e}")
        return
    
    if success:
        await message.answer("✅ Аккаунт успешно привязан! 🎉")
        
        # Проверяем, что привязка прошла
        try:
            user = await api_client.get_user_by_telegram(user_id)
            if user:
                await message.answer(
                    f"👤 <b>Привязан аккаунт:</b> {user.get('nickname')}\n"
                    f"📊 <b>Баланс:</b> {user.get('balance', 0)} ₽"
                )
        except Exception:
            pass
    else:
        await message.answer("❌ Ошибка привязки. Проверь ID и попробуй снова.")
