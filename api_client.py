import aiohttp
import asyncio
import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from config import Config

logger = logging.getLogger(__name__)

class APIClient:
    def __init__(self):
        self.base_url = Config.API_BASE_URL
        self.api_key = Config.BOT_API_KEY
        self.access_token: Optional[str] = None
        self.token_expires: Optional[datetime] = None
        self._session: Optional[aiohttp.ClientSession] = None
        self.telegram_id: Optional[str] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    def set_telegram_id(self, telegram_id: str):
        """Установить Telegram ID для авторизации"""
        self.telegram_id = telegram_id

    async def authenticate(self) -> str:
    """Получение JWT-токена"""
    # Убедимся, что telegram_id установлен
    if not self.telegram_id:
        raise Exception("telegram_id is required for authentication. Call set_telegram_id() first.")
    
    url = f"{self.base_url}/bot_api.php"
    data = {
        "api_key": self.api_key,
        "action": "auth",
        "telegram_id": self.telegram_id  # <-- ТЕПЕРЬ ПЕРЕДАЕТСЯ!
    }
    
    session = await self._get_session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "X-API-Key": self.api_key,
        "Content-Type": "application/json"
    }
    
    async with session.post(url, json=data, headers=headers) as resp:
        text = await resp.text()
        logger.info(f"Auth response: {text}")
        
        if not text or text.strip() == '':
            raise Exception("Empty response from server")
        
        try:
            result = json.loads(text)
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON: {text[:200]}")
        
        if result.get('error'):
            raise Exception(f"API error: {result['error']}")
        
        self.access_token = result.get('access_token')
        if not self.access_token:
            raise Exception(f"No access_token in response: {result}")
        
        expires_in = result.get('expires_in', 3600)
        self.token_expires = datetime.now() + timedelta(seconds=expires_in - 60)
        return self.access_token
        
        session = await self._get_session()
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }
        
        async with session.post(url, json=data, headers=headers) as resp:
            text = await resp.text()
            logger.info(f"Auth response status: {resp.status}")
            logger.info(f"Auth response: {text[:500]}")
            
            if resp.status != 200:
                raise Exception(f"Auth failed: {resp.status} - {text[:200]}")
            
            if not text or text.strip() == '':
                raise Exception("Empty response from server")
            
            try:
                result = json.loads(text)
            except json.JSONDecodeError as e:
                raise Exception(f"Invalid JSON response: {text[:200]}")
            
            if result.get('error'):
                raise Exception(f"API error: {result['error']}")
            
            self.access_token = result.get('access_token')
            if not self.access_token:
                raise Exception(f"No access_token in response: {result}")
            
            expires_in = result.get('expires_in', 3600)
            self.token_expires = datetime.now() + timedelta(seconds=expires_in - 60)
            return self.access_token

    async def _request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Универсальный метод для запросов к API"""
        if not self.access_token or datetime.now() > self.token_expires:
            await self.authenticate()
        
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        session = await self._get_session()
        
        for attempt in range(3):
            try:
                async with session.request(method, url, json=data, headers=headers) as resp:
                    if resp.status == 401:
                        await self.authenticate()
                        headers["Authorization"] = f"Bearer {self.access_token}"
                        continue
                    
                    if resp.status == 429:
                        retry_after = int(resp.headers.get('Retry-After', 5))
                        await asyncio.sleep(retry_after)
                        continue
                    
                    if resp.status >= 400:
                        error_text = await resp.text()
                        raise Exception(f"API error {resp.status}: {error_text}")
                    
                    return await resp.json()
                    
            except aiohttp.ClientError as e:
                if attempt == 2:
                    raise
                await asyncio.sleep(2 ** attempt)
        
        return {}

    async def get_user(self, telegram_id: int = None) -> Optional[Dict]:
        """Получить пользователя по Telegram ID"""
        if telegram_id:
            result = await self._request('GET', f'/bot_api.php?action=user&telegram_id={telegram_id}')
        elif self.telegram_id:
            result = await self._request('GET', f'/bot_api.php?action=user&telegram_id={self.telegram_id}')
        else:
            raise Exception("telegram_id is required")
        
        return result.get('user') if result.get('success') else None

    async def get_user_by_telegram(self, telegram_id: int) -> Optional[Dict]:
        """Получить пользователя по Telegram ID (аналог get_user)"""
        return await self.get_user(telegram_id)

    async def link_user(self, telegram_id: int, site_user_id: int) -> bool:
        """Привязать Telegram к аккаунту на сайте"""
        data = {
            'action': 'link',
            'api_key': self.api_key,
            'telegram_id': str(telegram_id),
            'site_user_id': site_user_id
        }
        result = await self._request('POST', '/bot_api.php', data)
        return result.get('success', False)

    async def unlink_user(self, site_user_id: int) -> bool:
        """Отвязать Telegram от аккаунта"""
        data = {
            'action': 'unlink',
            'api_key': self.api_key,
            'site_user_id': site_user_id
        }
        result = await self._request('POST', '/bot_api.php', data)
        return result.get('success', False)

    async def check_auth(self, telegram_id: int) -> bool:
        """Проверить, привязан ли пользователь"""
        result = await self._request('GET', f'/bot_api.php?action=check&telegram_id={telegram_id}')
        return result.get('authenticated', False)

    async def get_active_tournaments(self) -> List[Dict]:
        """Получить активные турниры"""
        # TODO: Добавить эндпоинт для турниров
        return []

    async def get_tournament_matches(self, tournament_id: int) -> List[Dict]:
        """Получить матчи турнира"""
        # TODO: Добавить эндпоинт для матчей
        return []

    async def get_match(self, match_id: int) -> Optional[Dict]:
        """Получить информацию о матче"""
        # TODO: Добавить эндпоинт для матча
        return None

    async def set_match_score(self, match_id: int, team1_score: int, team2_score: int) -> bool:
        """Установить счет матча"""
        # TODO: Добавить эндпоинт для счета
        return False

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
