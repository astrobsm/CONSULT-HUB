"""Generate the PWA PNG icons for the ConsultHUB frontend.

Run with the backend venv (Pillow required):
    backend/.venv/Scripts/python.exe scripts/generate_icons.py

Writes into frontend/public/. Re-run if the brand mark changes.
"""

from __future__ import annotations

import os

from PIL import Image, ImageDraw

BRAND = (30, 111, 217, 255)  # #1e6fd9
WHITE = (255, 255, 255, 255)
OUT = os.path.join(os.path.dirname(__file__), "..", "frontend", "public")


def _draw_mark(img: Image.Image, size: int) -> None:
    """A white ring + medical cross, centred (kept within the safe zone)."""
    d = ImageDraw.Draw(img)
    cx = cy = size / 2

    # Ring.
    r = size * 0.30
    ring_w = max(2, int(size * 0.055))
    d.ellipse(
        [cx - r, cy - r, cx + r, cy + r], outline=WHITE, width=ring_w
    )

    # Cross (plus) inside the ring.
    arm = size * 0.28  # full length of each arm
    thick = size * 0.095
    d.rounded_rectangle(
        [cx - thick / 2, cy - arm / 2, cx + thick / 2, cy + arm / 2],
        radius=thick * 0.35,
        fill=WHITE,
    )
    d.rounded_rectangle(
        [cx - arm / 2, cy - thick / 2, cx + arm / 2, cy + thick / 2],
        radius=thick * 0.35,
        fill=WHITE,
    )


def make_icon(size: int, *, rounded: bool) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if rounded:
        radius = int(size * 0.22)
        d.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=BRAND)
    else:
        d.rectangle([0, 0, size, size], fill=BRAND)  # maskable: full bleed
    _draw_mark(img, size)
    return img


def save(img: Image.Image, name: str) -> None:
    path = os.path.abspath(os.path.join(OUT, name))
    img.save(path, "PNG")
    print("wrote", path)


if __name__ == "__main__":
    save(make_icon(192, rounded=True), "icon-192.png")
    save(make_icon(512, rounded=True), "icon-512.png")
    save(make_icon(512, rounded=False), "icon-maskable-512.png")
    save(make_icon(180, rounded=True), "apple-touch-icon.png")
