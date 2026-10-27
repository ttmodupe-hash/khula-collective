"""Generate Khula-branded PWA icons using the project's Pillow dependency.

This is original vector-style geometry, not a third-party brand mark.
Run at Docker build time; no image-generation service or font assets needed.
"""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw

EMERALD = "#0E6F52"
SHADOW = "#073D31"
CREAM = "#FFF8DB"
GOLD = "#F5C66B"


def _render_icon(size, *, maskable=False):
    if size not in (192, 512):
        raise ValueError("Only 192px and 512px Khula app icons are supported.")
    scale = 4
    canvas = size * scale
    image = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    d = ImageDraw.Draw(image)
    rect = (0, 0, canvas - 1, canvas - 1)
    if maskable:
        d.rectangle(rect, fill=EMERALD)
    else:
        d.rounded_rectangle(rect, radius=int(canvas * .23), fill=EMERALD)
    def p(x, y):
        return int(x * canvas), int(y * canvas)
    def poly(points, color):
        d.polygon([p(x, y) for x, y in points], fill=color)

    # Unmistakable K, fully within the central maskable safe area.
    d.rounded_rectangle((*p(.31, .25), *p(.40, .75)),
                        radius=int(canvas * .014), fill=CREAM)
    poly([(.40,.52),(.58,.27),(.71,.27),(.52,.53),(.71,.73),
          (.58,.73),(.40,.53)], CREAM)
    # A rising gold accent distinguishes Khula from a generic initial.
    d.ellipse((*p(.68,.22), *p(.75,.29)), fill=GOLD)
    poly([(.66,.30),(.73,.30),(.73,.35)], GOLD)
    # Subtle base for a seed/growth motif, no financial return promise.
    d.rounded_rectangle((*p(.27,.79),*p(.73,.805)),
                        radius=int(canvas*.007), fill=SHADOW)
    return image.resize((size, size), Image.Resampling.LANCZOS)


def generate_icons(directory):
    dest = Path(directory)
    dest.mkdir(parents=True, exist_ok=True)
    variants = (
        ("khula-icon-192.png", 192, False),
        ("khula-icon-512.png", 512, False),
        ("khula-icon-maskable-512.png", 512, True),
    )
    for name, size, maskable in variants:
        icon = _render_icon(size, maskable=maskable)
        icon.save(dest / name, format="PNG", optimize=True)
    return [dest / name for name, _, _ in variants]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Khula PWA home-screen icons")
    parser.add_argument("--output-dir", default="static")
    args = parser.parse_args()
    for path in generate_icons(args.output_dir):
        print(path)
