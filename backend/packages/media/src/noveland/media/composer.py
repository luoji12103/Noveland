from __future__ import annotations

from collections.abc import Callable
from io import BytesIO

from PIL import Image


class ImageCompositionError(ValueError):
    pass


def compose_png(
    background_bytes: bytes,
    layers: list[tuple[bytes, int, int, int | None, int | None, float]],
) -> tuple[bytes, int, int, bool]:
    with Image.open(BytesIO(background_bytes)) as background:
        canvas = background.convert("RGBA")
        for layer_bytes, x, y, width, height, opacity in layers:
            with Image.open(BytesIO(layer_bytes)) as layer_image:
                layer = layer_image.convert("RGBA")
                if width is not None and height is not None:
                    layer = layer.resize((width, height), Image.Resampling.LANCZOS)
                if opacity < 1.0:
                    layer_opacity = opacity
                    alpha = layer.getchannel("A")
                    alpha = alpha.point(_opacity_scale(layer_opacity))
                    layer.putalpha(alpha)
                canvas.alpha_composite(layer, (x, y))
        output = BytesIO()
        canvas.save(output, format="PNG")
        return output.getvalue(), canvas.width, canvas.height, True


def _opacity_scale(opacity: float) -> Callable[[int], int]:
    def scale(value: int) -> int:
        return int(value * opacity)

    return scale
