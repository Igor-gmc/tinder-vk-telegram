# фоновый воркер: скачивание + InsightFace пайплайн

import logging
import aiohttp
from pathlib import Path
from dataclasses import dataclass, field

from src.infrastructure.vk.methods import VkMethods
from src.infrastructure.db.repositories import InMemoryUserRepo, PhotoDTO
from src.core.config import DATA_PATH, USE_INSIGHTFACE

_HAS_INSIGHTFACE = False
if USE_INSIGHTFACE:
    try:
        from src.infrastructure.vision.detector import FaceDetector
        from src.infrastructure.vision.photo_selector import select_top_photos
        _HAS_INSIGHTFACE = True
    except ImportError:
        pass

logger = logging.getLogger(__name__)


@dataclass
class PhotoProcessingService:
    vk: VkMethods
    user_repo: InMemoryUserRepo
    photos_dir: Path = DATA_PATH / 'photos'
    top_n: int = 3           # сколько лучших фото отбирать
    download_n: int = 10     # сколько фото скачивать для анализа InsightFace
    _detector: object | None = field(default=None, repr=False)

    def _get_detector(self):
        """Ленивая инициализация детектора (модель загружается один раз)."""
        if self._detector is None:
            self._detector = FaceDetector()
        return self._detector

    async def fetch_and_save_photos(self, access_token: str, vk_user_id: int) -> list[PhotoDTO]:
        """
        Полный пайплайн обработки фото кандидата:

        1) photos.get из VK → список фото с лайками
        2) Если 0 фото → вернуть пустой список (кандидат будет пропущен)
        3) Сортировка по лайкам, скачивание top download_n на диск
        4) Если скачано < 3 фото → пропускаем InsightFace, используем как есть
        5) Если >= 3 → прогоняем через InsightFace пайплайн:
           detect → filter (1 лицо, score, size) → blur → embed →
           cosine similarity (один человек) → top-3 selected
        6) Сохраняем результат в repo
        """
        # 1) получаем фото из VK
        data = await self.vk.photos_get(
            access_token=access_token,
            owner_id=vk_user_id,
        )

        items = data.get("response", {}).get("items", [])

        # 2) если фото нет — кандидат без фото
        if not items:
            logger.info('Кандидат %d: нет фото в профиле', vk_user_id)
            return []

        # парсим и сортируем по лайкам
        parsed = []
        for item in items:
            photo_id = item.get("id", 0)
            owner_id = item.get("owner_id", vk_user_id)
            likes_count = item.get("likes", {}).get("count", 0)

            url = self._get_best_url(item)
            if not url:
                continue

            parsed.append(PhotoDTO(
                photo_id=photo_id,
                owner_id=owner_id,
                url=url,
                likes_count=likes_count,
            ))

        if not parsed:
            return []

        parsed.sort(key=lambda p: p.likes_count, reverse=True)

        # 3) скачиваем top download_n для анализа
        to_download = parsed[:self.download_n]

        user_dir = self.photos_dir / str(vk_user_id)
        user_dir.mkdir(parents=True, exist_ok=True)

        downloaded = []
        for photo in to_download:
            local_path = await self._download_photo(photo, user_dir)
            if local_path:
                photo.local_path = str(local_path)
                downloaded.append(photo)

        if not downloaded:
            return []

        # 4) если < 3 скачанных фото — пропускаем InsightFace, используем как есть
        if len(downloaded) < 3:
            logger.info(
                'Кандидат %d: мало фото (%d), пропускаем InsightFace',
                vk_user_id, len(downloaded)
            )
            for photo in downloaded:
                photo.status = 'selected'
            await self.user_repo.set_photos(vk_user_id, downloaded)
            return downloaded

        # 5) >= 3 фото — прогоняем через InsightFace пайплайн (если доступен)
        if not _HAS_INSIGHTFACE:
            logger.info('Кандидат %d: insightface не установлен, fallback по лайкам', vk_user_id)
            fallback = downloaded[:self.top_n]
            for photo in fallback:
                photo.status = 'selected'
            await self.user_repo.set_photos(vk_user_id, fallback)
            return fallback

        logger.info('Кандидат %d: запуск InsightFace для %d фото', vk_user_id, len(downloaded))
        detector = self._get_detector()
        selected = select_top_photos(
            detector=detector,
            photos=downloaded,
            top_n=self.top_n,
        )

        # если InsightFace не выбрал ни одного — fallback на top-3 по лайкам
        if not selected:
            logger.warning('Кандидат %d: InsightFace не выбрал фото, fallback по лайкам', vk_user_id)
            fallback = downloaded[:self.top_n]
            for photo in fallback:
                photo.status = 'selected'
            await self.user_repo.set_photos(vk_user_id, fallback)
            return fallback

        # 6) сохраняем в repo
        await self.user_repo.set_photos(vk_user_id, selected)
        return selected

    def _get_best_url(self, item: dict) -> str | None:
        """Выбирает URL самого большого размера фото из sizes."""
        sizes = item.get("sizes", [])
        if not sizes:
            return None

        # VK sizes: s, m, x, o, p, q, r, y, z, w — w самый большой
        priority = {'w': 9, 'z': 8, 'y': 7, 'x': 6, 'r': 5, 'q': 4, 'p': 3, 'o': 2, 'm': 1, 's': 0}
        best = max(sizes, key=lambda s: priority.get(s.get("type", ""), -1))
        return best.get("url")

    async def _download_photo(self, photo: PhotoDTO, user_dir: Path) -> Path | None:
        """Скачивает одно фото на диск."""
        filename = f'{photo.photo_id}.jpg'
        filepath = user_dir / filename

        # если уже скачано — не качаем повторно
        if filepath.exists():
            return filepath

        try:
            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(photo.url, ssl=False) as resp:
                    if resp.status != 200:
                        return None
                    content = await resp.read()

            filepath.write_bytes(content)
            return filepath
        except (aiohttp.ClientError, OSError):
            return None
