import pytest
from PIL import ExifTags, ImageDraw
from PIL import Image as PILImage

from app.processing.colors import extract_colors
from app.processing.exif import extract_metadata

Base = ExifTags.Base
IFD = ExifTags.IFD
GPS = ExifTags.GPS

HEX_RE = r"^#[0-9a-f]{6}$"


def test_extract_colors_solid_image_returns_single_hex():
    img = PILImage.new("RGB", (50, 50), color=(255, 0, 0))
    colors = extract_colors(img)
    assert colors == ["#ff0000"]


def test_extract_colors_multi_color_image_returns_valid_hexes():
    img = PILImage.new("RGB", (100, 100), color=(255, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, 25, 100), fill=(0, 255, 0))
    draw.rectangle((20, 0, 50, 100), fill=(0, 0, 255))
    draw.rectangle((50, 0, 75, 100), fill=(255, 255, 0))

    colors = extract_colors(img)
    assert 1 <= len(colors) <= 5
    for c in colors:
        assert __import__("re").match(HEX_RE, c)


def test_extract_colors_respects_count_param():
    img = PILImage.new("RGB", (100, 100), color=(255, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, 50, 100), fill=(0, 255, 0))
    draw.rectangle((50, 0, 100, 100), fill=(0, 0, 255))

    colors = extract_colors(img, count=2)
    assert len(colors) <= 2


def test_extract_metadata_no_exif_returns_all_none():
    img = PILImage.new("RGB", (10, 10))
    meta = extract_metadata(img)
    assert meta == {"taken_at": None, "camera": None, "lens": None, "gps": None}


def test_extract_metadata_camera_from_make_model():
    img = PILImage.new("RGB", (10, 10))
    exif = img.getexif()
    exif[Base.Make.value] = "Canon"
    exif[Base.Model.value] = "EOS R5"

    meta = extract_metadata(img)
    assert meta["camera"] == "Canon EOS R5"


def test_extract_metadata_lens_from_exif_ifd():
    img = PILImage.new("RGB", (10, 10))
    exif = img.getexif()
    exif[Base.Make.value] = "Canon"
    exif_ifd = exif.get_ifd(IFD.Exif)
    exif_ifd[Base.LensModel.value] = "RF24-70mm F2.8"

    meta = extract_metadata(img)
    assert meta["lens"] == "RF24-70mm F2.8"


def test_extract_metadata_parses_taken_at():
    img = PILImage.new("RGB", (10, 10))
    exif = img.getexif()
    exif[Base.Make.value] = "Canon"
    exif_ifd = exif.get_ifd(IFD.Exif)
    exif_ifd[Base.DateTimeOriginal.value] = "2024:01:15 10:30:00"

    meta = extract_metadata(img)
    assert meta["taken_at"].isoformat() == "2024-01-15T10:30:00"


def test_extract_metadata_malformed_date_returns_none():
    img = PILImage.new("RGB", (10, 10))
    exif = img.getexif()
    exif[Base.Make.value] = "Canon"
    exif_ifd = exif.get_ifd(IFD.Exif)
    exif_ifd[Base.DateTimeOriginal.value] = "not-a-date"

    meta = extract_metadata(img)
    assert meta["taken_at"] is None


def test_extract_metadata_parses_gps_north_east():
    img = PILImage.new("RGB", (10, 10))
    exif = img.getexif()
    exif[Base.Make.value] = "Canon"
    gps_ifd = exif.get_ifd(IFD.GPSInfo)
    gps_ifd[GPS.GPSLatitude.value] = (40.0, 26.0, 46.32)
    gps_ifd[GPS.GPSLatitudeRef.value] = "N"
    gps_ifd[GPS.GPSLongitude.value] = (79.0, 58.0, 0.12)
    gps_ifd[GPS.GPSLongitudeRef.value] = "E"

    meta = extract_metadata(img)
    lat_str, lon_str = meta["gps"].split(",")
    assert float(lat_str) == pytest.approx(40.4462, abs=1e-4)
    assert float(lon_str) == pytest.approx(79.9667, abs=1e-4)


def test_extract_metadata_gps_south_west_is_negative():
    img = PILImage.new("RGB", (10, 10))
    exif = img.getexif()
    exif[Base.Make.value] = "Canon"
    gps_ifd = exif.get_ifd(IFD.GPSInfo)
    gps_ifd[GPS.GPSLatitude.value] = (40.0, 26.0, 46.32)
    gps_ifd[GPS.GPSLatitudeRef.value] = "S"
    gps_ifd[GPS.GPSLongitude.value] = (79.0, 58.0, 0.12)
    gps_ifd[GPS.GPSLongitudeRef.value] = "W"

    meta = extract_metadata(img)
    lat_str, lon_str = meta["gps"].split(",")
    assert float(lat_str) < 0
    assert float(lon_str) < 0


def test_extract_metadata_gps_missing_longitude_returns_none():
    img = PILImage.new("RGB", (10, 10))
    exif = img.getexif()
    exif[Base.Make.value] = "Canon"
    gps_ifd = exif.get_ifd(IFD.GPSInfo)
    gps_ifd[GPS.GPSLatitude.value] = (40.0, 26.0, 46.32)
    gps_ifd[GPS.GPSLatitudeRef.value] = "N"

    meta = extract_metadata(img)
    assert meta["gps"] is None
