from abc import ABC, abstractmethod
from typing import List, Optional

from infrastructure.db.schemas.dto import UserDTO, ProfileDTO, PhotoDTO


class UserRepository(ABC):

    # USERS
    @abstractmethod
    async def get_or_create_user(self, tg_user_id: int) -> UserDTO: ...

    @abstractmethod
    async def upsert_user_token_and_vk_id(
        self, tg_user_id: int, vk_access_token: str, vk_user_id: int
    ) -> None: ...

    @abstractmethod
    async def update_filters(
        self,
        tg_user_id: int,
        city: str,
        gender: int,
        age_from: int,
        age_to: int,
        city_id: Optional[int] = None,
    ) -> None: ...

    @abstractmethod
    async def get_cursor(self, tg_user_id: int) -> int: ...

    @abstractmethod
    async def set_cursor(self, tg_user_id: int, cursor: int) -> None: ...

    # FAVORITES
    @abstractmethod
    async def add_favorite(self, tg_user_id: int, vk_profile_id: int) -> None: ...

    @abstractmethod
    async def remove_favorite(self, tg_user_id: int, vk_profile_id: int) -> None: ...

    @abstractmethod
    async def list_favorites(self, tg_user_id: int) -> List[int]: ...

    # BLACKLIST
    @abstractmethod
    async def add_blacklist(self, tg_user_id: int, vk_profile_id: int) -> None: ...

    # QUEUE
    @abstractmethod
    async def set_queue(self, tg_user_id: int, vk_ids: List[int]) -> None: ...

    @abstractmethod
    async def get_queue(self, tg_user_id: int) -> List[int]: ...

    @abstractmethod
    async def get_current_vk_id(self, tg_user_id: int) -> Optional[int]: ...

    @abstractmethod
    async def move_next(self, tg_user_id: int) -> Optional[int]: ...

    @abstractmethod
    async def move_prev(self, tg_user_id: int) -> Optional[int]: ...

    # PROFILES
    @abstractmethod
    async def upsert_profile(self, profile: ProfileDTO) -> None: ...

    @abstractmethod
    async def get_profile(self, vk_user_id: int) -> Optional[ProfileDTO]: ...

    @abstractmethod
    async def set_photos(self, vk_user_id: int, photos: List[PhotoDTO]) -> None: ...

    @abstractmethod
    async def get_photos(self, vk_user_id: int) -> List[PhotoDTO]: ...