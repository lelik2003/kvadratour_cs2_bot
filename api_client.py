import aiohttp
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from config import Config
import logging

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
        url = f"{self.base_url}/auth"
        data = {"api_key": self.api_key}
        
        session = await self._get_session()
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; CS2TournamentBot/1.0)",
            "Accept": "application/json",
        }
        async with session.post(url, json=data, headers=headers) as resp:
            content_type = resp.headers.get("Content-Type", "")
            body_text = await resp.text()

            if resp.status != 200:
                raise Exception(f"Auth failed: {resp.status} - {body_text[:500]}")

            if "application/json" not in content_type:
                logger.error(
                    f"Ожидался JSON, получен Content-Type={content_type}. "
                    f"Начало тела ответа: {body_text[:500]}"
                )
                raise Exception(
                    f"Auth: сервер вернул не-JSON ответ ({content_type}). "
                    f"Проверь API_BASE_URL и защиту сайта (WAF/Cloudflare)."
                )

            import json as _json
            result = _json.loads(body_text)
            self.access_token = result.get('access_token')
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
            "Content-Type": "application/json"
        }
        
        session = await self._get_session()
        
        for attempt in range(3):
            try:
                async with session.request(method, url, json=data, headers=headers) as resp:
                    if resp.status == 401:
                        # Токен истек - обновляем
                        await self.authenticate()
                        headers["Authorization"] = f"Bearer {self.access_token}"
                        continue
                    
                    if resp.status == 429:
                        # Rate limit - ждем
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

    # ============================================
    # МЕТОДЫ ДЛЯ БОТА
    # ============================================

    async def get_user_by_telegram(self, telegram_id: int) -> Optional[Dict]:
        """Получить пользователя по Telegram ID"""
        result = await self._request('GET', f'/user?telegram_id={telegram_id}')
        return result.get('user') if result.get('success') else None

    async def link_user(self, telegram_id: int, site_user_id: int) -> bool:
        """Привязать Telegram к аккаунту на сайте"""
        data = {
            'telegram_id': str(telegram_id),
            'site_user_id': site_user_id
        }
        result = await self._request('POST', '/link', data)
        return result.get('success', False)

    async def unlink_user(self, user_id: int) -> bool:
        """Отвязать Telegram от аккаунта"""
        data = {'user_id': user_id}
        result = await self._request('POST', '/unlink', data)
        return result.get('success', False)

    async def get_active_tournaments(self) -> List[Dict]:
        """Получить активные турниры"""
        result = await self._request('GET', '/tournaments?status=active')
        return result.get('data', [])

    async def get_tournament_matches(self, tournament_id: int) -> List[Dict]:
        """Получить матчи турнира"""
        result = await self._request('GET', f'/tournaments/{tournament_id}/matches')
        return result.get('data', [])

    async def get_match(self, match_id: int) -> Optional[Dict]:
        """Получить информацию о матче"""
        result = await self._request('GET', f'/matches/{match_id}')
        return result.get('data')

    async def set_match_score(self, match_id: int, team1_score: int, team2_score: int) -> bool:
        """Установить счет матча"""
        data = {
            'team1_score': team1_score,
            'team2_score': team2_score,
            'status': 'finished'
        }
        result = await self._request('POST', f'/matches/{match_id}/score', data)
        return result.get('success', False)

    async def get_team_info(self, team_id: int) -> Optional[Dict]:
        """Получить информацию о команде"""
        result = await self._request('GET', f'/teams/{team_id}')
        return result.get('data')

    async def get_user_profile(self, user_id: int) -> Optional[Dict]:
        """Получить профиль пользователя"""
        result = await self._request('GET', f'/user?id={user_id}')
        return result.get('user')

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
