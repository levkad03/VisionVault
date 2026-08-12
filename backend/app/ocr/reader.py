from pathlib import Path

import numpy as np
from easyocr import Reader
from PIL import Image as PILImage

from app.core.config import settings

MODELS_DIR = Path(__file__).resolve().parents[2] / "models"

_reader: Reader | None = None


def _load() -> Reader:
    global _reader

    if _reader is None:
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        _reader = Reader(
            settings.ocr_languages_list,
            gpu=False,
            model_storage_directory=str(MODELS_DIR),
        )

    return _reader


def read_text(img: PILImage.Image) -> list[dict]:
    reader = _load()
    results = reader.readtext(np.array(img))

    detections = []
    for _, text, confidence in results:
        if confidence < settings.ocr_min_confidence:
            continue

        detections.append(
            {
                "text": text,
                "confidence": float(confidence),
                "language": settings.ocr_languages_list[0],
            }
        )

    return detections
