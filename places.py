"""places.py - standalone drawer for place JSON files.

Usage (test alone):
    python places.py streets.json street_day out.png

Use in code:
    from places import load_places, draw_place
    places = load_places("streets.json")
    img = draw_place(places, "street_day")                 # RGB image 540x960
    img = draw_place(places, "street_day", extra_shapes=[...])
"""
import json
import sys

from PIL import Image, ImageDraw

# Palette chosen by Claude (handoff section 10). Change here only.
PALETTE = {
    "main": (70, 150, 230),
    "main2": (70, 80, 110),
    "gold": (255, 200, 60),
    "steel": (120, 130, 150),
    "slate": (55, 60, 75),
    "sky": (150, 210, 245),
    "coral": (240, 110, 100),
    "orange": (255, 140, 20),
    "cyan": (77, 208, 225),
    "amber": (255, 183, 77),
    "navy": (22, 25, 36),
    "dark": (30, 30, 40),
    "white": (255, 255, 255),
    "skin": (242, 205, 165),
    "hair": (60, 40, 30),
}
FALLBACK_COLOR = (255, 0, 255)  # unknown colour name -> magenta, easy to spot


def load_places(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _rgba(shape, palette):
    rgb = palette.get(shape.get("c"), FALLBACK_COLOR)
    a = float(shape.get("a", 1))
    a = max(0.0, min(1.0, a))
    return rgb + (int(round(a * 255)),)


def _draw_shape(draw, shape, k, palette):
    t = shape.get("t", shape.get("type"))
    col = _rgba(shape, palette)
    if t == "rect":
        x, y, w, h = shape["x"], shape["y"], shape["w"], shape["h"]
        draw.rectangle([x * k, y * k, (x + w) * k, (y + h) * k], fill=col)
    elif t == "rrect":
        x, y, w, h = shape["x"], shape["y"], shape["w"], shape["h"]
        draw.rounded_rectangle([x * k, y * k, (x + w) * k, (y + h) * k],
                               radius=shape.get("r", 0) * k, fill=col)
    elif t == "circle":
        cx, cy, r = shape["cx"], shape["cy"], shape["r"]
        draw.ellipse([(cx - r) * k, (cy - r) * k, (cx + r) * k, (cy + r) * k], fill=col)
    elif t == "ellipse":
        cx, cy, rx, ry = shape["cx"], shape["cy"], shape["rx"], shape["ry"]
        draw.ellipse([(cx - rx) * k, (cy - ry) * k, (cx + rx) * k, (cy + ry) * k], fill=col)
    elif t == "poly":
        pts = [(px * k, py * k) for px, py in shape["pts"]]
        if len(pts) >= 3:
            draw.polygon(pts, fill=col)
    elif t == "line":
        draw.line([shape["x1"] * k, shape["y1"] * k, shape["x2"] * k, shape["y2"] * k],
                  fill=col, width=max(1, int(round(shape.get("w", 1) * k))))
    # unknown type: skipped on purpose, never breaks the scene


def draw_shapes(img, shapes, scale, palette=None):
    """Draw shapes in order (back to front) onto an RGBA image, with opacity."""
    palette = palette or PALETTE
    for shape in shapes:
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        try:
            _draw_shape(ImageDraw.Draw(layer), shape, scale, palette)
        except (KeyError, TypeError, ValueError):
            continue  # bad shape: skip it
        img.alpha_composite(layer)
    return img


def draw_place(places, name, size=(540, 960), extra_shapes=None, palette=None):
    """Return an RGB image of place `name`, plus optional extra shapes on top."""
    if name not in places:
        raise KeyError(f"unknown place: {name}")
    place = places[name]
    scale = size[0] / place.get("w", 100)
    img = Image.new("RGBA", size, (0, 0, 0, 255))
    draw_shapes(img, place["shapes"], scale, palette)
    if extra_shapes:
        draw_shapes(img, extra_shapes, scale, palette)
    return img.convert("RGB")


def draw_character(chars, name, height_px, colors=None):
    """Return a transparent RGBA image of character `name`, `height_px` tall."""
    if name not in chars:
        raise KeyError(f"unknown character: {name}")
    ch = chars[name]
    k = height_px / ch.get("h", 100)
    size = (max(1, int(round(ch.get("w", 60) * k))), max(1, int(round(ch.get("h", 100) * k))))
    palette = dict(PALETTE)
    if colors:
        palette.update(colors)
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw_shapes(img, ch["shapes"], k, palette)
    return img


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("usage: python places.py <places.json> <place_name> <out.png>")
        sys.exit(1)
    data = load_places(sys.argv[1])
    draw_place(data, sys.argv[2]).save(sys.argv[3])
    print("saved", sys.argv[3])
