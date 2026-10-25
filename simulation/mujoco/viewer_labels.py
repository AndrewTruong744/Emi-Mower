"""Small UUID labels whose pixel dimensions do not depend on the 3D viewport."""

import numpy as np
from PIL import Image, ImageDraw, ImageFont


FONT_PIXELS = 14
PADDING = 4


def uuid_label_image(mower_id, color):
    font = ImageFont.load_default(size=FONT_PIXELS)
    left, top, right, bottom = font.getbbox(mower_id)
    width = right - left + 2 * PADDING + 6
    height = bottom - top + 2 * PADDING
    image = Image.new("RGB", (width, height), (24, 24, 24))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 3, height - 1), fill=tuple(int(255 * value) for value in color))
    draw.text((PADDING + 6 - left, PADDING - top), mower_id, font=font, fill=(245, 245, 245))
    return np.asarray(image).copy()


def label_rectangle(camera, viewport, position, image_shape):
    """Project the anchor; keep the rendered text width and height in pixels."""
    height, width = image_shape[:2]
    if viewport.width < width or viewport.height < height:
        return None
    delta = np.asarray(position) - camera.pos
    depth = float(np.dot(delta, camera.forward))
    if depth <= camera.frustum_near:
        return None
    right = np.cross(camera.forward, camera.up)
    factor = 1.0 if camera.orthographic else camera.frustum_near / depth
    horizontal = float(np.dot(delta, right)) * factor
    vertical = float(np.dot(delta, camera.up)) * factor
    frustum_height = camera.frustum_top - camera.frustum_bottom
    frustum_width = camera.frustum_width or frustum_height * viewport.width / viewport.height
    x = viewport.left + (0.5 + (horizontal - camera.frustum_center) / frustum_width) * viewport.width
    y = viewport.bottom + (vertical - camera.frustum_bottom) / frustum_height * viewport.height
    if not (viewport.left <= x <= viewport.left + viewport.width
            and viewport.bottom <= y <= viewport.bottom + viewport.height):
        return None
    left = max(viewport.left, min(round(x - width / 2), viewport.left + viewport.width - width))
    bottom = max(viewport.bottom, min(round(y + 6), viewport.bottom + viewport.height - height))
    return left, bottom, width, height
