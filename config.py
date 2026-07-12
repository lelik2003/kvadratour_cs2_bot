import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Токен бота
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    
    # API сайта
    API_BASE_URL = os.getenv('API_BASE_URL')
    BOT_API_KEY = os.getenv('BOT_API_KEY')
    
    # Админы
    ADMIN_IDS = list(map(int, os.getenv('ADMIN_IDS', '').split(','))) if os.getenv('ADMIN_IDS') else []
    
    # Режим работы
    BOT_MODE = os.getenv('BOT_MODE', 'polling')
    WEBHOOK_URL = os.getenv('WEBHOOK_URL')
    WEBHOOK_PORT = int(os.getenv('WEBHOOK_PORT', 8443))
    
    @classmethod
    def validate(cls):
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN is required")
        if not cls.API_BASE_URL:
            raise ValueError("API_BASE_URL is required")
        if not cls.BOT_API_KEY:
            raise ValueError("BOT_API_KEY is required")