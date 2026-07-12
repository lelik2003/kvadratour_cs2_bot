import asyncio
import logging
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
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация бота
bot = Bot(
    token=Config.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

# Хранилище для состояний
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Клиент для API
api = APIClient()

# Регистрация обработчиков
dp.include_router(start.router)
dp.include_router(profile.router)
dp.include_router(tournaments.router)
dp.include_router(matches.router)
dp.include_router(admin.router)

async def on_startup():
    """Действия при запуске бота"""
    logger.info("🚀 Бот запускается...")
    await api.authenticate()
    logger.info("✅ Авторизация на API успешна")

async def on_shutdown():
    """Действия при остановке бота"""
    logger.info("🛑 Бот останавливается...")
    await api.close()
    await bot.session.close()
    logger.info("✅ Бот остановлен")

async def main():
    """Главная функция"""
    try:
        # Проверка конфигурации
        Config.validate()
        logger.info("✅ Конфигурация проверена")
        
        # Запуск бота
        await on_startup()
        
        if Config.BOT_MODE == 'webhook':
            # Режим вебхука
            from aiogram.webhook import webhook_server
            await bot.set_webhook(Config.WEBHOOK_URL)
            logger.info(f"✅ Вебхук установлен: {Config.WEBHOOK_URL}")
            
            # Запуск веб-сервера
            await webhook_server.run(
                app=dp,
                host='0.0.0.0',
                port=Config.WEBHOOK_PORT,
                bot=bot
            )
        else:
            # Режим поллинга (по умолчанию)
            logger.info("🔄 Запуск поллинга...")
            await dp.start_polling(bot)
            
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        raise
    finally:
        await on_shutdown()

if __name__ == "__main__":
    asyncio.run(main())