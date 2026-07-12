# api_client.py - обновленный

async def authenticate(self) -> str:
    """Получение токена"""
    # Используем bot_api.php вместо auth.php
    url = f"{self.base_url}/bot_api.php"
    data = {"api_key": self.api_key}
    
    session = await self._get_session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "X-API-Key": self.api_key
    }
    
    async with session.post(url, json=data, headers=headers) as resp:
        text = await resp.text()
        logger.info(f"Auth response status: {resp.status}")
        logger.info(f"Auth response body: {text[:300]}")
        
        if resp.status != 200:
            raise Exception(f"Auth failed: {resp.status} - {text[:200]}")
        
        try:
            result = json.loads(text)
        except json.JSONDecodeError:
            raise Exception(f"Invalid JSON response: {text[:200]}")
        
        if not result.get('success'):
            raise Exception(f"Auth error: {result.get('error', 'Unknown error')}")
        
        self.access_token = result.get('access_token')
        if not self.access_token:
            raise Exception(f"No access_token in response: {result}")
        
        expires_in = result.get('expires_in', 3600)
        self.token_expires = datetime.now() + timedelta(seconds=expires_in - 60)
        return self.access_token
