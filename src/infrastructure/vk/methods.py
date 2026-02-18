# users.search, photos.get, users.get, utils.resolveScreenName... 

from __future__ import annotations

from dataclasses import dataclass
from src.infrastructure.vk.client import VkClient


@dataclass(frozen=True)
class VkMethods:
    """
    Обёртка над VkClient: тут живут конкретные методы VK.
    """
    client: VkClient

    async def users_get_me(self, *, access_token: str) -> dict:
        """
        users.get без user_ids возвращает владельца токена.
        Это лучший способ проверить:
        - токен валиден
        - и узнать реальный vk_user_id владельца
        """
        return await self.client.call(
            "users.get",
            access_token=access_token,
            params={},  # user_ids не передаём специально
        )
