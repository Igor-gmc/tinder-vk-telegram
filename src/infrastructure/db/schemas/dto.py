from dataclasses import dataclass
from typing import Optional


@dataclass
class UserDTO:
    """
    Контейнер для User
    """
    tg_user_id: int
    vk_access_token: Optional[str] = None
    vk_user_id: Optional[int] = None
    filter_city_name: Optional[str] = None
    filter_city_id: Optional[int] = None
    filter_gender: Optional[int] = None
    filter_age_from: Optional[int] = None
    filter_age_to: Optional[int] = None
    history_cursor: int = 0


@dataclass
class ProfileDTO:
    """
    Контейнер для Profile
    """
    vk_user_id: int
    first_name: str
    last_name: str
    domain: str


@dataclass
class PhotoDTO:
    """
   Контейнер для Photo
    """
    photo_id: int
    owner_id: int
    url: str
    likes_count: int
    local_path: Optional[str] = None
    status: Optional[str] = None