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

    async def database_get_cities(
            self, *,
            access_token: str,
            q: str,
            country_id: int = 1,
            count: int = 1
    ) -> dict:
        """
        database.getCities — резолвит название города в city_id.
        country_id=1 — Россия по умолчанию.
        """
        return await self.client.call(
            "database.getCities",
            access_token=access_token,
            params={
                "country_id": country_id,
                "q": q,
                "count": count,
            },
        )

    async def users_search(
            self, *,
            access_token: str,
            city_id: int,
            sex: int,
            age_from: int,
            age_to: int,
            count: int = 50
    ) -> dict:
        """
        Поиск пользователей VK по city_id (числовой идентификатор города).
        """
        return await self.client.call(
            "users.search",
            access_token=access_token,
            params={
                "city": city_id,
                "sex": sex,
                "age_from": age_from,
                "age_to": age_to,
                "count": count,
                "has_photo": 1,
                "fields": "first_name,last_name,domain,city",
            },
        )

    async def photos_get(
            self, *,
            access_token: str,
            owner_id: int,
            album_id: str = 'profile',
            extended: int = 1,
            count: int = 50
    ) -> dict:
        """
        photos.get — получить фото пользователя.
        album_id='profile' — фото профиля.
        extended=1 — вернёт likes_count.
        """
        return await self.client.call(
            "photos.get",
            access_token=access_token,
            params={
                "owner_id": owner_id,
                "album_id": album_id,
                "extended": extended,
                "count": count,
                "photo_sizes": 1,
            },
        )
