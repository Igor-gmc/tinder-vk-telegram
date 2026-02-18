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

    async def add_favorite(self, tg_user_id: int, vk_profile_id: int) -> None:
        """Добавить vk id в избранное"""
        ...

    async def remove_favorite(self, tg_user_id: int, vk_profile_id: int) -> None:
        """Удалить vk id из избранного"""
        ...

    async def list_favorites(self, tg_user_id: int) -> list[int]:
        """
        Показать список избранного
        Возвращает отсортированный список vk id
        """
        ...
    
    async def add_blacklist(self, tg_user_id: int, vk_profile_id: int) -> None:
        """Добавить vk id в черный список"""
        ...

class InMemoryUserRepo: # заглушка для написания кодаа бота, чтобы сохранять данные в памяти вместо SQL
    def __init__(self):
        self._users: Dict[int, UserDTO] = {}
        self._favorites: Dict[int, set[int]] = {}
        self._black_list: Dict[int, set[int]] = {}

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


    async def add_favorite(self, tg_user_id: int, vk_profile_id: int) -> None:
        """Добавить vk id в избранное"""
        user = await self.get_or_create_user(tg_user_id)
        
        # получаем список избранного по tg id
        fav_set = self._favorites.get(user.tg_user_id)

        # провверяем создано ли хранилище
        if fav_set is None:
            fav_set = set()
            self._favorites[user.tg_user_id] = fav_set

        # добавляем vk id в set() с автоматическим удалением дублей
        fav_set.add(vk_profile_id)


    async def remove_favorite(self, tg_user_id: int, vk_profile_id: int) -> None:
        """Удалить vk id из избранного"""
        user = await self.get_or_create_user(tg_user_id)
        
        # получаем список избранного по tg id
        fav_set = self._favorites.get(user.tg_user_id)

        # провверяем
        if fav_set is None or not fav_set:
            return
        
        # discard при попытке удаления несуществующего элемента не уронит код
        fav_set.discard(vk_profile_id)

    async def list_favorites(self, tg_user_id: int) -> list[int]:
        """
        Показать список избранного
        Возвращает отсортированный список vk id
        """
        user = await self.get_or_create_user(tg_user_id)

         # получаем список избранного по tg id
        fav_set = self._favorites.get(user.tg_user_id, set())

        return sorted(fav_set)

    async def add_blacklist(self, tg_user_id: int, vk_profile_id: int) -> None:
        """Добавить vk id в черный список"""
        user = await self.get_or_create_user(tg_user_id)

        # получаем список чс по tg id
        bl_set = self._black_list.get(user.tg_user_id)

        # порверяем есть ли список
        if bl_set is None:
            bl_set = set()
            self._black_list[user.tg_user_id] = bl_set

        bl_set.add(vk_profile_id)