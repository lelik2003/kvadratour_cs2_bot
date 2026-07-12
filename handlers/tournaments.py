from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from api_client import APIClient  # <-- ТОЛЬКО ЭТОТ ИМПОРТ!

router = Router()
api = APIClient()  # <-- СОЗДАЕМ ЭКЗЕМПЛЯР ЗДЕСЬ

@router.message(Command("tournaments"))
async def cmd_tournaments(message: types.Message):
    """Список активных турниров"""
    tournaments = await api.get_active_tournaments()
    
    if not tournaments:
        await message.answer("❌ Активных турниров нет")
        return
    
    text = "🏆 <b>Активные турниры:</b>\n\n"
    
    for t in tournaments[:10]:
        text += f"""
<b>{t['name']}</b>
📋 Формат: {t['format']}
👥 Команд: {t['players_count']}/{t['max_teams']}
📊 Статус: {t['status']}
"""
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Матчи", callback_data=f"tournament_{t['id']}")],
            [InlineKeyboardButton(text="📝 Зарегистрироваться", callback_data=f"register_{t['id']}")]
        ])
        await message.answer(text, reply_markup=keyboard)
        text = ""

@router.callback_query(lambda c: c.data.startswith("tournament_"))
async def callback_tournament(callback: types.CallbackQuery):
    """Показать матчи турнира"""
    tournament_id = int(callback.data.split("_")[1])
    
    matches = await api.get_tournament_matches(tournament_id)
    
    if not matches:
        await callback.answer("Нет матчей в этом турнире")
        return
    
    text = f"📋 <b>Матчи турнира</b>\n\n"
    
    for m in matches[:10]:
        team1 = m.get('team1', {}).get('name', 'TBD')
        team2 = m.get('team2', {}).get('name', 'TBD')
        score1 = m.get('team1_score', 0)
        score2 = m.get('team2_score', 0)
        status = m.get('status', 'scheduled')
        
        status_emoji = {
            'scheduled': '⏳',
            'live': '🔴',
            'finished': '✅'
        }.get(status, '❓')
        
        text += f"{status_emoji} <b>{team1}</b> {score1}:{score2} <b>{team2}</b>\n"
    
    await callback.message.answer(text)
