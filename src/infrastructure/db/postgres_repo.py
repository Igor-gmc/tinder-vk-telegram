from sqlalchemy import select, delete, update, func
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from src.infrastructure.db.models import (
    User, Profile, Photo, FavoriteProfile, Blacklist, QueueItem,
)
from src.infrastructure.db.repositories import UserDTO, ProfileDTO, PhotoDTO


class PostgresUserRepo:
    """
    PostgreSQL реализация UserRepo Protocol.
    Drop-in замена InMemoryUserRepo.
    Принимает async_sessionmaker и создаёт сессию на каждую операцию.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._sf = session_factory

    # ================= USERS =================

    async def get_or_create_user(self, tg_user_id: int) -> UserDTO:
        async with self._sf() as s:
            result = await s.execute(
                select(User).where(User.tg_user_id == tg_user_id)
            )
            user = result.scalar_one_or_none()

            if not user:
                user = User(tg_user_id=tg_user_id, history_cursor=0)
                s.add(user)
                await s.commit()
                await s.refresh(user)

            return self._to_user_dto(user)

    async def upsert_user_token_and_vk_id(
        self, tg_user_id: int, vk_access_token: str, vk_user_id: int
    ) -> None:
        async with self._sf() as s:
            user = await self._get_or_create_model(s, tg_user_id)
            user.vk_access_token = vk_access_token
            user.vk_user_id = vk_user_id
            await s.commit()

    async def update_filters(
        self,
        tg_user_id: int,
        city: str,
        gender: int,
        age_from: int,
        age_to: int,
        city_id: int | None = None,
    ) -> None:
        async with self._sf() as s:
            user = await self._get_or_create_model(s, tg_user_id)

            user.filter_city_name = city
            user.filter_city_id = city_id
            user.filter_gender = gender
            user.filter_age_from = age_from
            user.filter_age_to = age_to
            user.history_cursor = 0

            # сбрасываем очередь при смене фильтров
            await s.execute(
                delete(QueueItem).where(QueueItem.tg_user_id == tg_user_id)
            )
            await s.commit()

    async def get_cursor(self, tg_user_id: int) -> int:
        async with self._sf() as s:
            result = await s.execute(
                select(User.history_cursor).where(User.tg_user_id == tg_user_id)
            )
            val = result.scalar_one_or_none()
            return val if val is not None else 0

    async def set_cursor(self, tg_user_id: int, cursor: int) -> None:
        async with self._sf() as s:
            user = await self._get_or_create_model(s, tg_user_id)
            user.history_cursor = cursor
            await s.commit()

    # ================= FAVORITES =================

    async def add_favorite(self, tg_user_id: int, vk_profile_id: int) -> None:
        async with self._sf() as s:
            # проверяем дубликат перед вставкой (избегаем IntegrityError)
            existing = await s.execute(
                select(FavoriteProfile).where(
                    FavoriteProfile.tg_user_id == tg_user_id,
                    FavoriteProfile.vk_profile_id == vk_profile_id,
                )
            )
            if existing.scalar_one_or_none() is None:
                s.add(FavoriteProfile(
                    tg_user_id=tg_user_id,
                    vk_profile_id=vk_profile_id,
                ))
                await s.commit()

    async def remove_favorite(self, tg_user_id: int, vk_profile_id: int) -> None:
        async with self._sf() as s:
            await s.execute(
                delete(FavoriteProfile).where(
                    FavoriteProfile.tg_user_id == tg_user_id,
                    FavoriteProfile.vk_profile_id == vk_profile_id,
                )
            )
            await s.commit()

    async def list_favorites(self, tg_user_id: int) -> list[int]:
        async with self._sf() as s:
            result = await s.execute(
                select(FavoriteProfile.vk_profile_id)
                .where(FavoriteProfile.tg_user_id == tg_user_id)
                .order_by(FavoriteProfile.vk_profile_id)
            )
            return list(result.scalars())

    # ================= BLACKLIST =================

    async def add_blacklist(self, tg_user_id: int, vk_profile_id: int) -> None:
        async with self._sf() as s:
            # проверяем дубликат
            existing = await s.execute(
                select(Blacklist).where(
                    Blacklist.tg_user_id == tg_user_id,
                    Blacklist.vk_profile_id == vk_profile_id,
                )
            )
            if existing.scalar_one_or_none() is None:
                s.add(Blacklist(
                    tg_user_id=tg_user_id,
                    vk_profile_id=vk_profile_id,
                ))

            # находим позицию кандидата в очереди
            queue_result = await s.execute(
                select(QueueItem).where(
                    QueueItem.tg_user_id == tg_user_id,
                    QueueItem.vk_profile_id == vk_profile_id,
                )
            )
            item = queue_result.scalar_one_or_none()

            if item is not None:
                removed_pos = item.position

                # удаляем из очереди
                await s.execute(
                    delete(QueueItem).where(
                        QueueItem.tg_user_id == tg_user_id,
                        QueueItem.vk_profile_id == vk_profile_id,
                    )
                )

                # сдвигаем позиции после удалённого элемента
                await s.execute(
                    update(QueueItem)
                    .where(
                        QueueItem.tg_user_id == tg_user_id,
                        QueueItem.position > removed_pos,
                    )
                    .values(position=QueueItem.position - 1)
                )

                # корректируем курсор (как в InMemoryUserRepo)
                user = await self._get_or_create_model(s, tg_user_id)
                queue_len_result = await s.execute(
                    select(func.count())
                    .select_from(QueueItem)
                    .where(QueueItem.tg_user_id == tg_user_id)
                )
                queue_len = queue_len_result.scalar()

                if removed_pos < user.history_cursor:
                    user.history_cursor -= 1
                elif removed_pos == user.history_cursor and user.history_cursor >= queue_len:
                    user.history_cursor = max(0, queue_len - 1)

            await s.commit()

    # ================= QUEUE =================

    async def set_queue(self, tg_user_id: int, vk_ids: list[int]) -> None:
        async with self._sf() as s:
            await s.execute(
                delete(QueueItem).where(QueueItem.tg_user_id == tg_user_id)
            )

            for pos, vk_id in enumerate(vk_ids):
                s.add(QueueItem(
                    tg_user_id=tg_user_id,
                    vk_profile_id=vk_id,
                    position=pos,
                ))

            user = await self._get_or_create_model(s, tg_user_id)
            user.history_cursor = 0

            await s.commit()

    async def get_queue(self, tg_user_id: int) -> list[int]:
        async with self._sf() as s:
            result = await s.execute(
                select(QueueItem.vk_profile_id)
                .where(QueueItem.tg_user_id == tg_user_id)
                .order_by(QueueItem.position)
            )
            return list(result.scalars())

    async def get_current_vk_id(self, tg_user_id: int) -> int | None:
        async with self._sf() as s:
            # получаем курсор
            cursor_result = await s.execute(
                select(User.history_cursor).where(User.tg_user_id == tg_user_id)
            )
            cursor = cursor_result.scalar_one_or_none()
            if cursor is None:
                return None

            # получаем vk_id по позиции = cursor (прямой SQL, без загрузки всей очереди)
            result = await s.execute(
                select(QueueItem.vk_profile_id)
                .where(
                    QueueItem.tg_user_id == tg_user_id,
                    QueueItem.position == cursor,
                )
            )
            return result.scalar_one_or_none()

    async def move_next(self, tg_user_id: int) -> int | None:
        async with self._sf() as s:
            user = await self._get_or_create_model(s, tg_user_id)

            # проверяем есть ли элемент на следующей позиции
            result = await s.execute(
                select(QueueItem.vk_profile_id)
                .where(
                    QueueItem.tg_user_id == tg_user_id,
                    QueueItem.position == user.history_cursor + 1,
                )
            )
            next_vk_id = result.scalar_one_or_none()

            if next_vk_id is not None:
                user.history_cursor += 1
                await s.commit()
                return next_vk_id

            return None

    async def move_prev(self, tg_user_id: int) -> int | None:
        async with self._sf() as s:
            user = await self._get_or_create_model(s, tg_user_id)

            if user.history_cursor <= 0:
                return None

            new_cursor = user.history_cursor - 1
            result = await s.execute(
                select(QueueItem.vk_profile_id)
                .where(
                    QueueItem.tg_user_id == tg_user_id,
                    QueueItem.position == new_cursor,
                )
            )
            vk_id = result.scalar_one_or_none()

            if vk_id is not None:
                user.history_cursor = new_cursor
                await s.commit()
                return vk_id

            return None

    # ================= PROFILES =================

    async def upsert_profile(self, profile: ProfileDTO) -> None:
        async with self._sf() as s:
            result = await s.execute(
                select(Profile).where(Profile.vk_user_id == profile.vk_user_id)
            )
            model = result.scalar_one_or_none()

            if model is None:
                model = Profile(
                    vk_user_id=profile.vk_user_id,
                    first_name=profile.first_name,
                    last_name=profile.last_name,
                    domain=profile.domain,
                )
                s.add(model)
            else:
                model.first_name = profile.first_name
                model.last_name = profile.last_name
                model.domain = profile.domain

            await s.commit()

    async def get_profile(self, vk_user_id: int) -> ProfileDTO | None:
        async with self._sf() as s:
            result = await s.execute(
                select(Profile).where(Profile.vk_user_id == vk_user_id)
            )
            model = result.scalar_one_or_none()

            if model is None:
                return None

            return ProfileDTO(
                vk_user_id=model.vk_user_id,
                first_name=model.first_name,
                last_name=model.last_name,
                domain=model.domain,
            )

    async def set_photos(self, vk_user_id: int, photos: list[PhotoDTO]) -> None:
        async with self._sf() as s:
            await s.execute(
                delete(Photo).where(Photo.vk_user_id == vk_user_id)
            )

            for p in photos:
                # явно передаём vk_user_id (FK на profiles)
                s.add(Photo(
                    vk_user_id=vk_user_id,
                    photo_id=p.photo_id,
                    owner_id=p.owner_id,
                    url=p.url,
                    likes_count=p.likes_count,
                    local_path=p.local_path,
                    status=p.status,
                    reject_reason=p.reject_reason,
                ))

            await s.commit()

    async def get_photos(self, vk_user_id: int) -> list[PhotoDTO]:
        async with self._sf() as s:
            result = await s.execute(
                select(Photo).where(Photo.vk_user_id == vk_user_id)
            )

            return [
                PhotoDTO(
                    photo_id=m.photo_id,
                    owner_id=m.owner_id,
                    url=m.url,
                    likes_count=m.likes_count,
                    local_path=m.local_path,
                    status=m.status,
                    reject_reason=m.reject_reason,
                )
                for m in result.scalars()
            ]

    # ================= HELPERS =================

    @staticmethod
    async def _get_or_create_model(s: AsyncSession, tg_user_id: int) -> User:
        result = await s.execute(
            select(User).where(User.tg_user_id == tg_user_id)
        )
        user = result.scalar_one_or_none()

        if user is None:
            user = User(tg_user_id=tg_user_id, history_cursor=0)
            s.add(user)
            await s.flush()

        return user

    @staticmethod
    def _to_user_dto(user: User) -> UserDTO:
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
