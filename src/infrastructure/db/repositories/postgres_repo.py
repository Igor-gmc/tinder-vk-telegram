from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from infrastructure.db.repositories.interfaces import UserRepository

from infrastructure.db.models import (
    User,
    Profile,
    Photo,
    FavoriteProfile,
    Blacklist,
    QueueItem,
)

from infrastructure.db.schemas.dto import UserDTO, ProfileDTO, PhotoDTO



class PostgresUserRepository(UserRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    # ================= USERS =================

    async def get_or_create_user(self, tg_user_id: int) -> UserDTO:
        result = await self.session.execute(
            select(User).where(User.tg_user_id == tg_user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            user = User(tg_user_id=tg_user_id)
            self.session.add(user)
            await self.session.commit()
            await self.session.refresh(user)

        return self._to_user_dto(user)

    async def upsert_user_token_and_vk_id(
        self, tg_user_id: int, vk_access_token: str, vk_user_id: int
    ) -> None:
        user = await self._get_or_create_user_model(tg_user_id)
        user.vk_access_token = vk_access_token
        user.vk_user_id = vk_user_id
        await self.session.commit()

    async def update_filters(
        self,
        tg_user_id: int,
        city: str,
        gender: int,
        age_from: int,
        age_to: int,
        city_id: int | None = None,
    ) -> None:
        user = await self._get_or_create_user_model(tg_user_id)

        user.filter_city_name = city
        user.filter_gender = gender
        user.filter_age_from = age_from
        user.filter_age_to = age_to
        user.filter_city_id = city_id
        user.history_cursor = 0

        await self.session.execute(
            delete(QueueItem).where(QueueItem.tg_user_id == tg_user_id)
        )

        await self.session.commit()

    async def get_cursor(self, tg_user_id: int) -> int:
        result = await self.session.execute(
            select(User.history_cursor).where(User.tg_user_id == tg_user_id)
        )
        return result.scalar_one_or_none() or 0

    async def set_cursor(self, tg_user_id: int, cursor: int) -> None:
        user = await self._get_or_create_user_model(tg_user_id)
        user.history_cursor = cursor
        await self.session.commit()

    # ================= FAVORITES =================

    async def add_favorite(self, tg_user_id: int, vk_profile_id: int) -> None:
        self.session.add(FavoriteProfile(
            tg_user_id=tg_user_id,
            vk_profile_id=vk_profile_id
        ))
        await self.session.commit()

    async def remove_favorite(self, tg_user_id: int, vk_profile_id: int) -> None:
        await self.session.execute(
            delete(FavoriteProfile).where(
                FavoriteProfile.tg_user_id == tg_user_id,
                FavoriteProfile.vk_profile_id == vk_profile_id,
            )
        )
        await self.session.commit()

    async def list_favorites(self, tg_user_id: int) -> list[int]:
        result = await self.session.execute(
            select(FavoriteProfile.vk_profile_id)
            .where(FavoriteProfile.tg_user_id == tg_user_id)
        )
        return list(result.scalars())

    # ================= BLACKLIST =================

    async def add_blacklist(self, tg_user_id: int, vk_profile_id: int) -> None:
        self.session.add(Blacklist(
            tg_user_id=tg_user_id,
            vk_profile_id=vk_profile_id
        ))
        await self.session.execute(
            delete(QueueItem).where(
                QueueItem.tg_user_id == tg_user_id,
                QueueItem.vk_profile_id == vk_profile_id,
            )
        )
        await self.session.commit()

    # ================= QUEUE =================

    async def set_queue(self, tg_user_id: int, vk_ids: list[int]) -> None:
        await self.session.execute(
            delete(QueueItem).where(QueueItem.tg_user_id == tg_user_id)
        )

        for pos, vk_id in enumerate(vk_ids):
            self.session.add(QueueItem(
                tg_user_id=tg_user_id,
                vk_profile_id=vk_id,
                position=pos,
            ))

        user = await self._get_or_create_user_model(tg_user_id)
        user.history_cursor = 0

        await self.session.commit()

    async def get_queue(self, tg_user_id: int) -> list[int]:
        result = await self.session.execute(
            select(QueueItem.vk_profile_id)
            .where(QueueItem.tg_user_id == tg_user_id)
            .order_by(QueueItem.position)
        )
        return list(result.scalars())

    async def get_current_vk_id(self, tg_user_id: int) -> int | None:
        queue = await self.get_queue(tg_user_id)
        cursor = await self.get_cursor(tg_user_id)
        if 0 <= cursor < len(queue):
            return queue[cursor]
        return None

    async def move_next(self, tg_user_id: int) -> int | None:
        user = await self._get_or_create_user_model(tg_user_id)
        queue = await self.get_queue(tg_user_id)

        if user.history_cursor + 1 < len(queue):
            user.history_cursor += 1
            await self.session.commit()
            return queue[user.history_cursor]

        return None

    async def move_prev(self, tg_user_id: int) -> int | None:
        user = await self._get_or_create_user_model(tg_user_id)
        queue = await self.get_queue(tg_user_id)

        if user.history_cursor > 0:
            user.history_cursor -= 1
            await self.session.commit()
            return queue[user.history_cursor]

        return None

    # ================= PROFILES =================

    async def upsert_profile(self, profile: ProfileDTO) -> None:
        result = await self.session.execute(
            select(Profile).where(Profile.vk_user_id == profile.vk_user_id)
        )
        model = result.scalar_one_or_none()

        if not model:
            model = Profile(**profile.__dict__)
            self.session.add(model)
        else:
            model.first_name = profile.first_name
            model.last_name = profile.last_name
            model.domain = profile.domain

        await self.session.commit()

    async def get_profile(self, vk_user_id: int) -> ProfileDTO | None:
        result = await self.session.execute(
            select(Profile).where(Profile.vk_user_id == vk_user_id)
        )
        model = result.scalar_one_or_none()

        if not model:
            return None

        return ProfileDTO(
            vk_user_id=model.vk_user_id,
            first_name=model.first_name,
            last_name=model.last_name,
            domain=model.domain,
        )

    async def set_photos(self, vk_user_id: int, photos: list[PhotoDTO]) -> None:
        await self.session.execute(
            delete(Photo).where(Photo.vk_user_id == vk_user_id)
        )

        for p in photos:
            self.session.add(Photo(**p.__dict__))

        await self.session.commit()

    async def get_photos(self, vk_user_id: int) -> list[PhotoDTO]:
        result = await self.session.execute(
            select(Photo).where(Photo.vk_user_id == vk_user_id)
        )
        models = result.scalars().all()

        return [
            PhotoDTO(
                photo_id=m.photo_id,
                owner_id=m.owner_id,
                url=m.url,
                likes_count=m.likes_count,
                local_path=m.local_path,
                status=m.status,
            )
            for m in models
        ]

    # ================= INTERNAL =================

    async def _get_or_create_user_model(self, tg_user_id: int) -> User:
        result = await self.session.execute(
            select(User).where(User.tg_user_id == tg_user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            user = User(tg_user_id=tg_user_id)
            self.session.add(user)
            await self.session.flush()

        return user

    def _to_user_dto(self, user: User) -> UserDTO:
        return UserDTO(
            tg_user_id=user.tg_user_id,
            vk_access_token=user.vk_access_token,
            vk_user_id=user.vk_user_id,
            filter_city_name=user.filter_city_name,
            filter_city_id=user.filter_city_id,
            filter_gender=user.filter_gender,
            filter_age_from=user.filter_age_from,
            filter_age_to=user.filter_age_to,
            history_cursor=user.history_cursor,
        )