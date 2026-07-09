import open_clip
import torch
from PIL import Image as PILImage

from app.core.config import settings

_model = None
_preprocess = None
_tokenizer = None


def _load() -> None:
    global _model, _preprocess, _tokenizer
    if _model is None:
        _model, _, _preprocess = open_clip.create_model_and_transforms(
            settings.clip_model_name, pretrained=settings.clip_pretrained
        )
        _tokenizer = open_clip.get_tokenizer(settings.clip_model_name)
        _model.eval()


def encode_image(image: PILImage.Image) -> list[float]:
    _load()
    with torch.no_grad():
        tensor = _preprocess(image).unsqueeze(0)
        features = _model.encode_image(tensor)
        features /= features.norm(dim=-1, keepdim=True)

    return features.squeeze(0).tolist()


def encode_text(text: str) -> list[float]:
    _load()
    with torch.no_grad():
        tokens = _tokenizer([text])
        features = _model.encode_text(tokens)
        features /= features.norm(dim=-1, keepdim=True)

    return features.squeeze(0).tolist()
