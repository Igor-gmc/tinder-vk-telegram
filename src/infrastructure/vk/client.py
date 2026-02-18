# HTTP-клиент VK (token per user, retry/backoff)

import aiohttp
from dataclasses import dataclass
from typing import Any

import asyncio

from src.core.config import VK_API_VERSION
from src.core.exceptions import VkApiError

@dataclass(frozen=True)
class VkClient:
    """
    Низкоуровневый HTTP-клиент VK.
    Он умеет:
    - собрать URL и параметры
    - сделать запрос
    - распарсить JSON
    - если VK вернул "error" — поднять VkApiError
    - если сеть/таймаут — тоже поднять VkApiError
    """
    api_version = VK_API_VERSION
    base_url ='https://api.vk.com/method'
    timeout_sec = 10
    retries = 2                             # количество повторов при сетевых проблемах

    async def call(self, method: str, *, access_token: str, params: dict[str, Any]) -> dict[str, Any]:
        """
        Универсальный вызов VK метода.
        method: "users.get", "photos.get" и т.д.
        access_token: пользовательский токен
        params: параметры метода (без access_token и v — добавим сами)
        """
        # собираем ссылку с методом
        url = f'{self.base_url}/{method}'

        # собираем параметры обращения
        payload = dict(params)
        payload['access_token'] = access_token
        payload['v'] = self.api_version

        timeout = aiohttp.ClientTimeout(total=self.timeout_sec)

        # при ошибке соединения
        last_excp: Exception | None = None

        for attempt in range(self.retries):
            try:
                # на каждый вызов создаем сессию
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url, params=payload, ssl=False) as resp:
                        data = await resp.json(content_type=None)

                # Если VK API возвращает ошибки в поле "error"
                if isinstance(data, dict) and 'error' in data:
                    err = data['error']
                    raise VkApiError(
                        code=int(err.get('error_code', -1)),
                        msg=str(err.get('error_msg', 'Unknow VK error')),
                        raw=data
                    )
                
                return data
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:

                last_excp = e

                if attempt < self.retries - 1:
                    await asyncio.sleep(0.4 * (attempt + 1))
                else:
                    raise VkApiError(-1000, f"Network/timeout error: {e!r}") from e
        raise VkApiError(-1001, "Unexpected VK client error") from last_excp
