import logging
from pathlib import Path
from .files import is_arw

log = logging.getLogger(__name__)


def should_skip(raw: Path, jpeg: Path) -> bool:
    return jpeg.is_file() and jpeg.stat().st_size > 0 and jpeg.stat().st_mtime_ns > raw.stat().st_mtime_ns


def convert_all(source: Path, output: Path, quality: int = 95):
    import rawpy
    from PIL import Image, ImageCms

    output.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in source.iterdir() if p.is_file() and is_arw(p.name))
    result = {"completed": 0, "skipped": 0, "failed": 0, "failures": []}
    profile = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    for i, raw in enumerate(files, 1):
        jpeg = output / f"{raw.stem}.jpg"
        if should_skip(raw, jpeg):
            result["skipped"] += 1
            log.info("[%d/%d] JPEG already current: %s", i, len(files), jpeg.name)
            continue
        temporary = jpeg.with_suffix(".jpg.part")
        try:
            log.info("[%d/%d] Converting %s -> %s", i, len(files), raw.name, jpeg.name)
            with rawpy.imread(str(raw)) as image:
                rgb = image.postprocess(use_camera_wb=True, output_bps=8,
                                        half_size=False, output_color=rawpy.ColorSpace.sRGB)
            with Image.fromarray(rgb) as image:
                image.save(temporary, format="JPEG", quality=quality, subsampling=0,
                           icc_profile=profile)
            temporary.replace(jpeg)
            result["completed"] += 1
        except Exception:
            result["failed"] += 1
            result["failures"].append(raw.name)
            log.exception("Conversion failed: %s", raw)
        finally:
            temporary.unlink(missing_ok=True)
    return result
