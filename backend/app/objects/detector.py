from PIL import Image as PILImage
from ultralytics import YOLO
from ultralytics.engine.results import Results

from app.core.config import settings

_model: YOLO | None = None


def _load() -> YOLO:
    global _model
    if _model is None:
        _model = YOLO(settings.yolo_model_name)

    return _model


def detect_objects(img: PILImage.Image) -> list[dict]:
    model = _load()
    results = model.predict(img, conf=settings.object_min_confidence, verbose=False)

    detections = []
    for result in results:
        if not isinstance(result, Results) or result.boxes is None:
            continue

        boxes = result.boxes
        for i in range(len(boxes)):
            detections.append(
                {
                    "class_name": result.names[int(boxes.cls[i])],
                    "confidence": float(boxes.conf[i]),
                    "bounding_box": [float(v) for v in boxes.xyxy[i].tolist()],
                }
            )

    return detections
