import open_clip
import torch
from PIL import Image as PILImage

from app.core.config import settings

_model = None
_preprocess = None


def _load() -> None:
    global _model, _preprocess
    if _model is None:
        _model, _, _preprocess = open_clip.create_model_and_transforms(
            settings.clip_model_name, pretrained=settings.clip_pretrained
        )
        _model.eval()


def encode_image(image: PILImage.Image) -> list[float]:
    _load()
    with torch.no_grad():
        tensor = _preprocess(image).unsqueeze(0)
        features = _model.encode_image(tensor)
        features /= features.norm(dim=-1, keepdim=True)

    return features.squeeze(0).tolist()
