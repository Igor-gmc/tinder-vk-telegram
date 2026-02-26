# variance of Laplacian: calc_blur_score → float

import cv2
import numpy as np


# порог: ниже этого значения фото считается размытым
MIN_BLUR_SCORE = 50.0


def calc_blur_score(image_path: str, bbox: np.ndarray) -> float:
    """
    Оценка резкости кропа лица через variance of Laplacian.
    Чем выше значение — тем резче изображение.

    image_path: путь к изображению
    bbox: [x1, y1, x2, y2] — координаты лица
    """
    img = cv2.imread(image_path)
    if img is None:
        return 0.0

    # вырезаем кроп лица
    x1, y1, x2, y2 = [int(c) for c in bbox]

    # ограничиваем координаты размерами изображения
    h, w = img.shape[:2]
    x1 = max(0, x1)
    y1 = max(0, y1)
    x2 = min(w, x2)
    y2 = min(h, y2)

    if x2 <= x1 or y2 <= y1:
        return 0.0

    crop = img[y1:y2, x1:x2]

    # конвертируем в градации серого
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)

    # variance of Laplacian
    score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    return score
