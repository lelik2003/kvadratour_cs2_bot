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

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def authenticate(self) -> str:
        """Получение JWT-токена"""
        url = f"{self.base_url}/auth.php"
        data = {"api_key": self.api_key}
        
        session = await self._get_session()
        
        # Эмуляция браузера
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Cache-Control": "no-cache"
        }
        
        async with session.post(url, json=data, headers=headers) as resp:
            text = await resp.text()
            logger.info(f"Auth response status: {resp.status}")
            logger.info(f"Auth response body: {text[:300]}")
            
            if resp.status != 200:
                raise Exception(f"Auth failed: {resp.status} - {text[:200]}")
            
            # Проверяем, что это JSON, а не HTML
            if text.strip().startswith('<'):
                # Это HTML — значит защита сработала
                raise Exception(f"Server returned HTML instead of JSON. Check if API endpoint is accessible: {url}")
            
            try:
                result = json.loads(text)
            except json.JSONDecodeError:
                raise Exception(f"Invalid JSON response: {text[:200]}")
            
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
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
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

    async def get_user_by_telegram(self, telegram_id: int) -> Optional[Dict]:
        result = await self._request('GET', f'/user.php?telegram_id={telegram_id}')
        return result.get('user') if result.get('success') else None

    async def link_user(self, telegram_id: int, site_user_id: int) -> bool:
        data = {
            'telegram_id': str(telegram_id),
            'site_user_id': site_user_id
        }
        result = await self._request('POST', '/link.php', data)
        return result.get('success', False)

    async def get_active_tournaments(self) -> List[Dict]:
        result = await self._request('GET', '/tournaments.php?status=active')
        return result.get('data', [])

    async def get_tournament_matches(self, tournament_id: int) -> List[Dict]:
        result = await self._request('GET', f'/tournaments.php?id={tournament_id}&matches=true')
        return result.get('data', [])

    async def get_match(self, match_id: int) -> Optional[Dict]:
        result = await self._request('GET', f'/matches.php?id={match_id}')
        return result.get('data')

    async def set_match_score(self, match_id: int, team1_score: int, team2_score: int) -> bool:
        data = {
            'team1_score': team1_score,
            'team2_score': team2_score,
            'status': 'finished'
        }
        result = await self._request('POST', f'/matches.php?id={match_id}&action=score', data)
        return result.get('success', False)

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
