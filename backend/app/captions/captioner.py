from pathlib import Path

from PIL import Image as PILImage
from transformers import BlipForConditionalGeneration, BlipProcessor

from app.core.config import settings

MODELS_DIR = Path(__file__).resolve().parents[2] / "models"

_bundle: tuple[BlipProcessor, BlipForConditionalGeneration] | None = None


def _load() -> tuple[BlipProcessor, BlipForConditionalGeneration]:
    global _bundle

    if _bundle is None:
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        _processor = BlipProcessor.from_pretrained(
            settings.caption_model_name, cache_dir=str(MODELS_DIR)
        )
        _model = BlipForConditionalGeneration.from_pretrained(
            settings.caption_model_name, cache_dir=str(MODELS_DIR)
        )

        _model.eval()

        _bundle = (_processor, _model)

    return _bundle


def generate_caption(img: PILImage.Image) -> str:
    processor, model = _load()

    inputs = processor(img, return_tensors="pt")
    output = model.generate(**inputs, max_new_tokens=50)
    return processor.decode(output[0], skip_special_tokens=True)
