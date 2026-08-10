from PIL import Image as PILImage

PALETTE_SIZE = (150, 150)
COLOR_COUNT = 5


def extract_colors(img: PILImage.Image, count: int = COLOR_COUNT) -> list[str]:
    small = img.convert("RGB")
    small.thumbnail(PALETTE_SIZE)

    quantized = small.quantize(colors=count)
    palette = quantized.getpalette()
    color_counts = quantized.getcolors()

    if not palette or not color_counts:
        return []

    color_counts.sort(key=lambda c: c[0], reverse=True)

    hex_colors = []
    for _, index in color_counts[:count]:
        if not isinstance(index, int):
            continue
        r, g, b = palette[index * 3 : index * 3 + 3]
        hex_colors.append(f"#{r:02x}{g:02x}{b:02x}")

    return hex_colors
