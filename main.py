import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from config import Config
from api_client import APIClient
from handlers import start, profile, tournaments, matches, admin

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Инициализация бота
bot = Bot(
    token=Config.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Создаем клиент API
api_client = APIClient()

# Регистрируем обработчики
dp.include_router(start.router)
dp.include_router(profile.router)
dp.include_router(tournaments.router)
dp.include_router(matches.router)
dp.include_router(admin.router)

async def on_startup():
    """Действия при запуске бота"""
    logger.info("🚀 Бот запускается...")
    
    try:
        # Получаем ID бота для авторизации
        bot_info = await bot.get_me()
        bot_telegram_id = str(bot_info.id)
        logger.info(f"🤖 Bot ID: {bot_telegram_id}")
        
        # Устанавливаем Telegram ID для авторизации
        api_client.set_telegram_id(bot_telegram_id)
        
        # Авторизуемся на API
        await api_client.authenticate()
        logger.info("✅ Авторизация на API успешна")
        
        # Получаем информацию о боте как пользователе
        user = await api_client.get_user()
        if user:
            logger.info(f"👤 Бот авторизован как: {user.get('nickname')} (ID: {user.get('id')})")
        else:
            logger.warning("⚠️ Бот не привязан к аккаунту на сайте")
            logger.info("💡 Для привязки используйте команду /link в боте")
            
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске: {e}")
        # Продолжаем запуск даже если авторизация не удалась

async def on_shutdown():
    """Действия при остановке бота"""
    logger.info("🛑 Бот останавливается...")
    await api_client.close()
    await bot.session.close()
    logger.info("✅ Бот остановлен")

async def main():
    """Главная функция"""
    try:
        # Проверка конфигурации
        Config.validate()
        logger.info("✅ Конфигурация проверена")
        
        await on_startup()
        
        logger.info("🔄 Запуск поллинга...")
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        raise
    finally:
        await on_shutdown()

if __name__ == "__main__":
    asyncio.run(main())
