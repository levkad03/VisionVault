from datetime import datetime

from PIL import ExifTags
from PIL import Image as PILImage


def extract_metadata(img: PILImage.Image) -> dict:
    exif = img.getexif()

    if not exif:
        return {"taken_at": None, "camera": None, "lens": None, "gps": None}

    exif_ifd = exif.get_ifd(ExifTags.IFD.Exif)
    gps_ifd = exif.get_ifd(ExifTags.IFD.GPSInfo)

    make = exif.get(ExifTags.Base.Make.value, "").strip(" \x00")
    model = exif.get(ExifTags.Base.Model.value, "").strip(" \x00")
    camera = f"{make} {model}".strip() or None

    lens = exif_ifd.get(ExifTags.Base.LensModel.value, "").strip(" \x00") or None

    taken_at = None

    raw_date = exif_ifd.get(ExifTags.Base.DateTimeOriginal.value)
    if raw_date:
        try:
            taken_at = datetime.strptime(raw_date, "%Y:%m:%d %H:%M:%S")
        except ValueError:
            taken_at = None

    gps = _parse_gps(gps_ifd) if gps_ifd else None

    return {"taken_at": taken_at, "camera": camera, "lens": lens, "gps": gps}


def _parse_gps(gps_ifd: dict) -> str | None:
    lat = gps_ifd.get(ExifTags.GPS.GPSLatitude.value)
    lat_ref = gps_ifd.get(ExifTags.GPS.GPSLatitudeRef.value)
    lon = gps_ifd.get(ExifTags.GPS.GPSLongitude.value)
    lon_ref = gps_ifd.get(ExifTags.GPS.GPSLongitudeRef.value)

    if not (lat and lon and lat_ref and lon_ref):
        return None

    lat_deg = _dms_to_decimal(lat, lat_ref)
    lon_deg = _dms_to_decimal(lon, lon_ref)
    return f"{lat_deg:.6f},{lon_deg:.6f}"


def _dms_to_decimal(dms: tuple, ref: str) -> float:
    degrees, minutes, seconds = (float(v) for v in dms)
    decimal = degrees + minutes / 60 + seconds / 3600
    return -decimal if ref in ("S", "W") else decimal
