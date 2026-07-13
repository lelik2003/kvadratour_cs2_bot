import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from config import Config
from api_client import APIClient

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
