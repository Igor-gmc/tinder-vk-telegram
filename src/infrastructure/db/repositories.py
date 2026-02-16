# Заглушка для написания бота

from typing import Optional, Protocol, Dict
from dataclasses import dataclass

@dataclass
class UserDTO: #dataclass с полями пользователя
    tg_user_id: int
    vk_access_token: Optional[str] = None
    vk_user_id: Optional[int] = None
    filter_city_name: Optional[str] = None
    filter_gender: Optional[int] = None
    filter_age_from: Optional[int] = None
    filter_age_to: Optional[int] = None
    history_cursor: int = 0

class UserRepo(Protocol): #методы для MVP
    async def get_or_create_user(self, tg_user_id: int) -> UserDTO:
        """Найди пользователя и верни его
        если пользователя нет, создай и верни пользователя
        """
        ...

    async def upsert_user_token_and_vk_id(
            self,
            tg_user_id: int, 
            vk_access_token: str, 
            vk_user_id: int
            ) -> None:
        """создай если нет, затем запиши токен+vk_id"""
        ...

    async def update_filters(
            self,
            tg_user_id: int, 
            city: str, 
            gender: int, 
            age_from: int, 
            age_to: int
            ) -> None:
        """создай если нет, затем запиши фильтры, и сбрось cursor=0"""
        ...

    async def get_cursor(self, tg_user_id: int) -> int:
        """если пользователя нет — верни 0"""
        ...

    async def set_cursor(self, tg_user_id: int, cursor: int) -> None:
        """создай если нет, затем сохрани cursor"""
        ...

class InMemoryUserRepo: # заглушка для написания кодаа бота, чтобы сохранять данные в памяти вместо SQL
    def __init__(self):
        self._users: Dict[int, UserDTO] = {}

    async def get_or_create_user(self, tg_user_id: int) -> UserDTO:
        """Найди пользователя и верни его
        если пользователя нет, создай и верни пользователя
        """
        # ищем пользователя tg
        user = self._users.get(tg_user_id)
        
        # если не находим, то создаем нового пользователя
        if user is None:
            user = UserDTO(tg_user_id=tg_user_id)
            self._users[tg_user_id] = user
        
        # Возвращаем пользователя TG
        return user

    async def upsert_user_token_and_vk_id(
            self,
            tg_user_id: int, 
            vk_access_token: str, 
            vk_user_id: int
            ) -> None:
        """создай если нет, затем запиши токен + vk_id"""

        # Ищем пользователя tg, если не находим, то создаем нового пользователя
        user = await self.get_or_create_user(tg_user_id)
        
        # записываем параметры VK пользователя
        user.vk_access_token = vk_access_token
        user.vk_user_id = vk_user_id


    async def update_filters(
            self,
            tg_user_id: int, 
            city: str, 
            gender: int, 
            age_from: int, 
            age_to: int
            ) -> None:
        """создай если нет, затем запиши фильтры, и сбрось cursor=0"""
        
        # Ищем пользователя
        user = await self.get_or_create_user(tg_user_id)

        # записываем фильтры
        user.filter_city_name = city
        user.filter_gender = gender
        user.filter_age_from = age_from
        user.filter_age_to = age_to

        user.history_cursor = 0


    async def get_cursor(self, tg_user_id: int) -> int:
        """если пользователя нет — верни 0"""
        user = await self.get_or_create_user(tg_user_id)
        return user.history_cursor



    async def set_cursor(self, tg_user_id: int, cursor: int) -> None:
        """создай если нет, затем сохрани cursor"""
        user = await self.get_or_create_user(tg_user_id)
        user.history_cursor = cursor