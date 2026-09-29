"""Small standard-library image helpers used by the workflow runner."""

from __future__ import annotations

import struct
from pathlib import Path


def png_dimensions(path: str | Path) -> tuple[int, int] | None:
    try:
        with Path(path).open("rb") as handle:
            header = handle.read(24)
        if len(header) >= 24 and header[:8] == b"\x89PNG\r\n\x1a\n":
            return struct.unpack(">II", header[16:24])
    except OSError:
        return None
    return None


def png_has_transparency(path: str | Path) -> bool | None:
    """Return whether a PNG has an alpha channel with transparent pixels."""
    try:
        from PIL import Image  # type: ignore[import-not-found]

        with Image.open(path) as image:
            alpha = image.convert("RGBA").getchannel("A")
            return alpha.getextrema()[0] < 255
    except ImportError:
        return None
    except OSError:
        return False


def prepare_product_canvas(source: str | Path, destination: str | Path,
                          width: int, height: int) -> Path:
    """Place an RGBA product on a transparent canvas without resizing its pixels."""
    try:
        from PIL import Image  # type: ignore[import-not-found]
    except ImportError as error:
        raise RuntimeError("Pillow is required to prepare transparent product PNGs; install ComfyUI dependencies first") from error
    source_path = Path(source)
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source_path) as opened:
        image = opened.convert("RGBA")
    alpha_min, alpha_max = image.getchannel("A").getextrema()
    if alpha_min == 255:
        raise ValueError("Product PNG has no transparent pixels. Remove its background before compositing.")
    if alpha_max == 0:
        raise ValueError("Product PNG is fully transparent and contains no visible product pixels.")
    if image.width > width or image.height > height:
        raise ValueError(
            f"Product PNG ({image.width}x{image.height}) is larger than the selected canvas ({width}x{height}). "
            "Resize it uniformly or provide a matching transparent canvas; the source is never resized automatically."
        )
    if image.size == (width, height):
        image.save(target, format="PNG")
        return target
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    left = (width - image.width) // 2
    top = (height - image.height) // 2
    canvas.alpha_composite(image, (left, top))
    canvas.save(target, format="PNG")
    return target
