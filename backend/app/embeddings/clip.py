import open_clip
import torch
from PIL import Image as PILImage

from app.core.config import settings

_model = None
_preprocess = None
_tokenizer = None


def _load():
    global _model, _preprocess, _tokenizer
    if _model is None:
        _model, _, _preprocess = open_clip.create_model_and_transforms(
            settings.clip_model_name, pretrained=settings.clip_pretrained
        )
        _tokenizer = open_clip.get_tokenizer(settings.clip_model_name)
        _model.eval()
    return _model, _preprocess, _tokenizer


def encode_image(image: PILImage.Image) -> list[float]:
    model, preprocess, _ = _load()
    with torch.no_grad():
        tensor = preprocess(image).unsqueeze(0)
        features = model.encode_image(tensor)
        features /= features.norm(dim=-1, keepdim=True)

    return features.squeeze(0).tolist()


def encode_text(text: str) -> list[float]:
    model, _, tokenizer = _load()
    with torch.no_grad():
        tokens = tokenizer([text])
        features = model.encode_text(tokens)
        features /= features.norm(dim=-1, keepdim=True)

    return features.squeeze(0).tolist()
