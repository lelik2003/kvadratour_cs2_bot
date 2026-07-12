import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from config import Config
from api_client import APIClient  # <-- Импортируем из api_client, а не из main
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

# Создаем клиент API (ОДИН раз здесь)
api_client = APIClient()

# Регистрируем обработчики
dp.include_router(start.router)
dp.include_router(profile.router)
dp.include_router(tournaments.router)
dp.include_router(matches.router)
dp.include_router(admin.router)

async def on_startup():
    logger.info("🚀 Бот запускается...")
    await api_client.authenticate()
    logger.info("✅ Авторизация на API успешна")

async def on_shutdown():
    logger.info("🛑 Бот останавливается...")
    await api_client.close()
    await bot.session.close()

async def main():
    try:
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
