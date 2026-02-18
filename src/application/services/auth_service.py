# сохранить токен, протестировать VK соединение  

from __future__ import annotations

from dataclasses import dataclass

from src.core.exceptions import VkApiError
from src.infrastructure.vk.methods import VkMethods
from src.infrastructure.db.repositories import UserRepo  # Protocol (или реальный тип)


@dataclass
class AuthService:
    """
    AuthService — бизнес-логика авторизации.

    Он НЕ знает про Telegram handlers.
    Он знает только:
    - токен
    - введённый пользователем vk_id
    - репозиторий, куда сохранить
    - VK методы, чтобы проверить
    """
    vk: VkMethods
    user_repo: UserRepo

    async def authorize(self, *, tg_user_id: int, access_token: str, expected_vk_user_id: int) -> int:
        """
        Основной use-case:
        - проверить токен в VK
        - проверить совпадение vk_id
        - сохранить токен+vk_id в БД/репо
        - вернуть реальный vk_id (владельца токена)

        Если что-то не так — бросаем VkApiError.
        """
        # 1) Проверяем токен и получаем владельца токена
        data = await self.vk.users_get_me(access_token=access_token)

        # Ожидаем формат: {"response":[{"id":..., ...}]}
        resp = data.get("response", [])
        if not resp:
            raise VkApiError(-2, "Empty response from VK", raw=data)

        real_vk_id = int(resp[0].get("id", 0))
        if not real_vk_id:
            raise VkApiError(-3, "VK did not return user id", raw=data)

        # 2) Сверяем введённый vk_id с владельцем токена
        if real_vk_id != expected_vk_user_id:
            raise VkApiError(
                -4,
                f"VK_ID не совпадает с владельцем токена. В токене: {real_vk_id}, вы ввели: {expected_vk_user_id}",
                raw=data,
            )

        # 3) Сохраняем данные авторизации (в твоём MVP — InMemoryUserRepo)
        await self.user_repo.upsert_user_token_and_vk_id(
            tg_user_id=tg_user_id,
            vk_access_token=access_token,
            vk_user_id=real_vk_id,
        )

        return real_vk_id
