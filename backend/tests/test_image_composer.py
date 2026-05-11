from __future__ import annotations

from io import BytesIO

from noveland.media.composer import compose_png
from PIL import Image


def test_compose_png_respects_alpha_and_z_order() -> None:
    background = _png((0, 0, 255, 255), 2, 2)
    red = _png((255, 0, 0, 255), 2, 2)
    green = _png((0, 255, 0, 255), 1, 1)

    output, width, height, has_alpha = compose_png(
        background,
        [
            (red, 0, 0, None, None, 1.0),
            (green, 0, 0, None, None, 1.0),
        ],
    )

    with Image.open(BytesIO(output)) as image:
        assert image.convert("RGBA").getpixel((0, 0)) == (0, 255, 0, 255)
        assert image.convert("RGBA").getpixel((1, 1)) == (255, 0, 0, 255)
    assert (width, height, has_alpha) == (2, 2, True)


def _png(color: tuple[int, int, int, int], width: int, height: int) -> bytes:
    image = Image.new("RGBA", (width, height), color)
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()
