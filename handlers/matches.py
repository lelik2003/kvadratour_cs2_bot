from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from loader import api

router = Router()

class MatchScore(StatesGroup):
    """Состояния для ввода счета"""
    waiting_for_match_id = State()
    waiting_for_score = State()

@router.message(Command("match"))
async def cmd_match(message: types.Message):
    """Поиск матча по ID"""
    args = message.text.split()
    
    if len(args) < 2:
        await message.answer(
            "❌ Укажи ID матча.\n"
            "Пример: <code>/match 123</code>"
        )
        return
    
    try:
        match_id = int(args[1])
    except ValueError:
        await message.answer("❌ ID должен быть числом")
        return
    
    match_data = await api.get_match(match_id)
    
    if not match_data:
        await message.answer(f"❌ Матч #{match_id} не найден")
        return
    
    team1 = match_data.get('team1', {}).get('name', 'TBD')
    team2 = match_data.get('team2', {}).get('name', 'TBD')
    score1 = match_data.get('team1_score', 0)
    score2 = match_data.get('team2_score', 0)
    status = match_data.get('status', 'scheduled')
    
    status_emoji = {
        'scheduled': '⏳ Ожидается',
        'live': '🔴 Идёт',
        'finished': '✅ Завершён'
    }.get(status, '❓')
    
    text = f"""
🎯 <b>Матч #{match_id}</b>

<b>{team1}</b> {score1}:{score2} <b>{team2}</b>

📊 Статус: {status_emoji}
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Обновить", callback_data=f"refresh_match_{match_id}")],
        [InlineKeyboardButton(text="✏️ Ввести счёт", callback_data=f"set_score_{match_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_start")]
    ])
    
    await message.answer(text, reply_markup=keyboard)

@router.callback_query(lambda c: c.data.startswith("set_score_"))
async def callback_set_score(callback: types.CallbackQuery, state: FSMContext):
    """Начать ввод счета"""
    match_id = int(callback.data.split("_")[2])
    await state.update_data(match_id=match_id)
    await state.set_state(MatchScore.waiting_for_score)
    
    await callback.message.answer(
        f"✏️ Введи счет для матча #{match_id} в формате:\n"
        "<code>13:10</code>\n\n"
        "Где первое число — победа команды 1, второе — команды 2"
    )

@router.message(MatchScore.waiting_for_score)
async def process_score(message: types.Message, state: FSMContext):
    """Обработка введенного счета"""
    data = await state.get_data()
    match_id = data.get('match_id')
    
    if not match_id:
        await message.answer("❌ Ошибка: ID матча не найден")
        await state.clear()
        return
    
    # Парсим счет
    try:
        parts = message.text.split(':')
        if len(parts) != 2:
            raise ValueError
        score1 = int(parts[0].strip())
        score2 = int(parts[1].strip())
    except ValueError:
        await message.answer(
            "❌ Неверный формат. Используй: <code>13:10</code>"
        )
        return
    
    # Обновляем счет
    success = await api.set_match_score(match_id, score1, score2)
    
    if success:
        await message.answer(f"✅ Счет обновлен: {score1}:{score2}")
    else:
        await message.answer("❌ Ошибка обновления счета")
    
    await state.clear()
