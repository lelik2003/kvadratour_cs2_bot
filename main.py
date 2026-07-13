import asyncio
import logging
from config import Config
from loader import bot, dp, api
from handlers import start, profile, tournaments, matches, admin

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
            # Режим вебхука (aiogram 3.x, актуальный API)
            from aiohttp import web
            from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

            await bot.set_webhook(Config.WEBHOOK_URL)
            logger.info(f"✅ Вебхук установлен: {Config.WEBHOOK_URL}")

            app = web.Application()
            SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path="/webhook")
            setup_application(app, dp, bot=bot)

            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, host='0.0.0.0', port=Config.WEBHOOK_PORT)
            await site.start()

            # Держим приложение живым
            await asyncio.Event().wait()
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
