# оркестратор: detect → filter → blur → embed → cosine similarity → топ-3

import logging
from dataclasses import dataclass, field
from pathlib import Path

from src.infrastructure.vision.detector import FaceDetector, DetectedFace
from src.infrastructure.vision.embedder import get_embedding, cosine_similarity
from src.infrastructure.vision.blur_check import calc_blur_score, MIN_BLUR_SCORE
from src.infrastructure.db.repositories import PhotoDTO

logger = logging.getLogger(__name__)

# порог косинусного сходства для "один и тот же человек"
SAME_PERSON_THRESHOLD = 0.4


@dataclass
class AnalyzedPhoto:
    """Фото после анализа InsightFace."""
    photo_dto: PhotoDTO
    face: DetectedFace
    blur_score: float


@dataclass
class FaceGroup:
    """Группа фото с одним и тем же человеком."""
    photos: list[AnalyzedPhoto] = field(default_factory=list)

    def matches(self, candidate: AnalyzedPhoto) -> bool:
        """Проверяет, совпадает ли кандидат с кем-то из группы."""
        cand_emb = get_embedding(candidate.face)
        for member in self.photos:
            member_emb = get_embedding(member.face)
            if cosine_similarity(cand_emb, member_emb) >= SAME_PERSON_THRESHOLD:
                return True
        return False


def select_top_photos(
        detector: FaceDetector,
        photos: list[PhotoDTO],
        top_n: int = 3,
) -> list[PhotoDTO]:
    """
    Пайплайн выбора фото — последовательная обработка:

    1) Берём первое фото, анализируем (detect → filter → blur), сохраняем в группу
    2) Берём следующее фото, анализируем. Сравниваем эмбеддинг с фото в каждой группе:
       - если совпадает с группой → добавляем в эту группу
       - если не совпадает ни с одной → создаём новую группу
    3) Повторяем, пока в какой-то группе не наберётся top_n фото
       или пока не закончатся фото
    4) Берём самую большую группу, ранжируем по лайкам → top_n = selected

    Возвращает список PhotoDTO (до top_n штук) с обновлёнными статусами.
    """
    groups: list[FaceGroup] = []

    for photo in photos:
        if not photo.local_path or not Path(photo.local_path).exists():
            photo.status = 'rejected'
            photo.reject_reason = 'error'
            continue

        # детекция лиц
        faces = detector.detect(photo.local_path)

        # фильтр: ровно 1 лицо, det_score, размер
        face = detector.filter_single_face(faces)
        if face is None:
            reason = _get_reject_reason(faces)
            photo.status = 'rejected'
            photo.reject_reason = reason
            logger.debug('Фото %s отклонено: %s', photo.photo_id, reason)
            continue

        # blur-check
        blur_score = calc_blur_score(photo.local_path, face.bbox)
        if blur_score < MIN_BLUR_SCORE:
            photo.status = 'rejected'
            photo.reject_reason = 'blurry'
            logger.debug('Фото %s отклонено: blurry (blur=%.1f)', photo.photo_id, blur_score)
            continue

        # фото прошло все фильтры — промежуточный статус accepted
        photo.status = 'accepted'
        analyzed = AnalyzedPhoto(photo_dto=photo, face=face, blur_score=blur_score)

        # ищем подходящую группу
        matched_group = None
        for group in groups:
            if group.matches(analyzed):
                matched_group = group
                break

        if matched_group is not None:
            matched_group.photos.append(analyzed)
            # если набрали top_n фото одного человека — сразу выходим
            if len(matched_group.photos) >= top_n:
                logger.info(
                    'Кандидат %s: набрано %d фото одного человека, досрочный выход',
                    photo.owner_id, top_n
                )
                break
        else:
            # новый человек — создаём новую группу
            new_group = FaceGroup(photos=[analyzed])
            groups.append(new_group)

    if not groups:
        return []

    # берём самую большую группу
    best_group = max(groups, key=lambda g: len(g.photos))

    # ранжируем лучшую группу по лайкам, берём top_n
    best_group.photos.sort(key=lambda a: a.photo_dto.likes_count, reverse=True)
    selected = best_group.photos[:top_n]

    for a in selected:
        a.photo_dto.status = 'selected'

    # остальные в лучшей группе остаются accepted (прошли фильтры, но не в top-N)
    # фото из других групп тоже остаются accepted

    result = [a.photo_dto for a in selected]
    logger.info(
        'Выбрано %d/%d фото для кандидата %s (групп лиц: %d)',
        len(result), len(photos),
        photos[0].owner_id if photos else '?',
        len(groups)
    )
    return result


def _get_reject_reason(faces: list[DetectedFace]) -> str:
    """Определяет причину отклонения фото по результатам детекции."""
    if len(faces) == 0:
        return 'no_face'
    if len(faces) > 1:
        return 'multi_face'
    face = faces[0]
    from src.infrastructure.vision.detector import MIN_DET_SCORE, MIN_FACE_SIZE
    if face.det_score < MIN_DET_SCORE:
        return 'low_score'
    if face.face_width < MIN_FACE_SIZE or face.face_height < MIN_FACE_SIZE:
        return 'small_face'
    return 'unknown'
