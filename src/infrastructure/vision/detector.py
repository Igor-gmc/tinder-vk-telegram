# SCRFD: detect(image_path) → list[DetectedFace]

import logging
import cv2
import numpy as np
from dataclasses import dataclass, field
from pathlib import Path
from insightface.app import FaceAnalysis

from src.core.config import DATA_PATH, INSIGHTFACE_MODEL

logger = logging.getLogger(__name__)

# пороги фильтрации
MIN_DET_SCORE = 0.5       # минимальная уверенность детектора
MIN_FACE_SIZE = 50        # минимальный размер лица в пикселях (по стороне bbox)


@dataclass
class DetectedFace:
    """Результат детекции одного лица на фото."""
    bbox: np.ndarray           # [x1, y1, x2, y2]
    det_score: float
    landmark: np.ndarray       # 5 точек
    embedding: np.ndarray      # 512-d ArcFace (L2-нормирован)

    @property
    def face_width(self) -> float:
        return float(self.bbox[2] - self.bbox[0])

    @property
    def face_height(self) -> float:
        return float(self.bbox[3] - self.bbox[1])


class FaceDetector:
    """
    Обёртка над InsightFace FaceAnalysis (SCRFD + ArcFace).
    Загружает модель buffalo_l один раз, переиспользует для всех фото.
    """

    def __init__(self, models_dir: Path | None = None, det_size: tuple[int, int] = (640, 640)):
        root = str(models_dir or DATA_PATH / 'models')
        self._app = FaceAnalysis(
            name=INSIGHTFACE_MODEL,
            root=root,
            providers=['CPUExecutionProvider'],
        )
        self._app.prepare(ctx_id=0, det_size=det_size)
        logger.info('FaceDetector инициализирован (%s, CPU)', INSIGHTFACE_MODEL)

    def detect(self, image_path: str) -> list[DetectedFace]:
        """
        Детектирует лица на изображении.
        Возвращает список DetectedFace с bbox, score, landmark, embedding.
        """
        img = cv2.imread(image_path)
        if img is None:
            logger.warning('Не удалось прочитать изображение: %s', image_path)
            return []

        faces = self._app.get(img)

        result = []
        for f in faces:
            result.append(DetectedFace(
                bbox=f.bbox,
                det_score=float(f.det_score),
                landmark=f.landmark,
                embedding=f.normed_embedding,
            ))

        return result

    def filter_single_face(self, faces: list[DetectedFace]) -> DetectedFace | None:
        """
        Фильтрация:
        - ровно 1 лицо
        - det_score выше порога
        - лицо не слишком мелкое
        Возвращает Face или None (фото отклонено).
        """
        if len(faces) != 1:
            return None

        face = faces[0]

        if face.det_score < MIN_DET_SCORE:
            return None

        if face.face_width < MIN_FACE_SIZE or face.face_height < MIN_FACE_SIZE:
            return None

        return face
