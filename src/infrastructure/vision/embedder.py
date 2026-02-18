# ArcFace: get_embedding(face) → ndarray(512) + cosine similarity

import numpy as np
from src.infrastructure.vision.detector import DetectedFace


def get_embedding(face: DetectedFace) -> np.ndarray:
    """
    Извлечь 512-мерный эмбеддинг из DetectedFace.
    Эмбеддинг уже вычислен FaceAnalysis и L2-нормирован.
    """
    return face.embedding


def cosine_similarity(emb_a: np.ndarray, emb_b: np.ndarray) -> float:
    """
    Косинусное сходство двух L2-нормированных эмбеддингов.
    Для нормированных векторов: cos_sim = dot(a, b).
    """
    return float(np.dot(emb_a, emb_b))
