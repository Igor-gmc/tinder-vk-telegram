# предыдущий/следующий кандидат + показать карточку

import logging
from dataclasses import dataclass, field
from src.infrastructure.vk.methods import VkMethods
from src.infrastructure.db.repositories import InMemoryUserRepo, ProfileDTO

logger = logging.getLogger(__name__)

PRELOAD_BUFFER = 5  # количество анкет, подготовленных впереди курсора


@dataclass
class DatingService:
    vk: VkMethods
    user_repo: InMemoryUserRepo
    _photo_service: object | None = field(default=None, repr=False)

    async def resolve_city_id(self, access_token: str, city_name: str) -> int | None:
        """
        Резолвит название города в числовой city_id через VK database.getCities.
        Возвращает city_id первого совпадения, или None если город не найден.
        """
        data = await self.vk.database_get_cities(
            access_token=access_token,
            q=city_name,
            count=1,
        )

        items = data.get("response", {}).get("items", [])
        if not items:
            return None
        return int(items[0]["id"])

    async def ensure_queue(self, tg_user_id: int) -> None:
        """
        Если очередь пуста — резолвим city_id, делаем users.search,
        сохраняем профили кандидатов и очередь VK_ID.
        """
        user = await self.user_repo.get_or_create_user(tg_user_id)
        queue = await self.user_repo.get_queue(tg_user_id)
        if queue:
            return

        if not user.vk_access_token:
            return

        # фильтры должны быть заполнены
        if not user.filter_city_name or not user.filter_gender or not user.filter_age_from or not user.filter_age_to:
            return

        # резолвим city_id если ещё не сохранён
        city_id = user.filter_city_id
        if city_id is None:
            city_id = await self.resolve_city_id(
                access_token=user.vk_access_token,
                city_name=user.filter_city_name,
            )
            if city_id is None:
                return
            # сохраняем city_id чтобы не резолвить повторно
            user.filter_city_id = city_id

        data = await self.vk.users_search(
            access_token=user.vk_access_token,
            city_id=city_id,
            sex=user.filter_gender,
            age_from=user.filter_age_from,
            age_to=user.filter_age_to,
            count=50,
        )

        items = data.get("response", {}).get("items", [])
        vk_ids = []

        for it in items:
            if "id" not in it:
                continue
            vk_id = int(it["id"])
            vk_ids.append(vk_id)

            # сохраняем профиль кандидата в repo
            profile = ProfileDTO(
                vk_user_id=vk_id,
                first_name=it.get("first_name", ""),
                last_name=it.get("last_name", ""),
                domain=it.get("domain", ""),
            )
            await self.user_repo.upsert_profile(profile)

        await self.user_repo.set_queue(tg_user_id, vk_ids)

    async def get_candidate_card(self, tg_user_id: int) -> tuple[ProfileDTO | None, list]:
        """
        Возвращает (ProfileDTO, [PhotoDTO]) текущего кандидата.
        Если кандидата нет — (None, []).
        """
        vk_id = await self.user_repo.get_current_vk_id(tg_user_id)
        if vk_id is None:
            return None, []

        profile = await self.user_repo.get_profile(vk_id)
        photos = await self.user_repo.get_photos(vk_id)
        return profile, photos

    async def next_candidate(self, tg_user_id: int) -> int | None:
        await self.ensure_queue(tg_user_id)
        return await self.user_repo.move_next(tg_user_id)

    async def prev_candidate(self, tg_user_id: int) -> int | None:
        await self.ensure_queue(tg_user_id)
        return await self.user_repo.move_prev(tg_user_id)

    async def preload_ahead(self, tg_user_id: int) -> None:
        """
        Подгружает фото для следующих PRELOAD_BUFFER кандидатов впереди курсора.
        Вызывать после next_candidate, чтобы буфер готовых анкет не иссякал.
        """
        if self._photo_service is None:
            return

        user = await self.user_repo.get_or_create_user(tg_user_id)
        if not user.vk_access_token:
            return

        q = await self.user_repo.get_queue(tg_user_id)
        if not q:
            return

        cursor = user.history_cursor
        # берём до PRELOAD_BUFFER кандидатов впереди курсора
        ahead = q[cursor + 1: cursor + 1 + PRELOAD_BUFFER]

        for vk_id in ahead:
            # если фото уже подготовлены — пропускаем
            existing = await self.user_repo.get_photos(vk_id)
            if existing:
                continue

            try:
                await self._photo_service.fetch_and_save_photos(
                    access_token=user.vk_access_token,
                    vk_user_id=vk_id,
                )
                logger.info('Предзагрузка: фото кандидата %d готовы', vk_id)
            except Exception:
                logger.warning('Предзагрузка: ошибка для кандидата %d', vk_id, exc_info=True)
