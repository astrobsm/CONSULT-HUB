"""QR code generation (pure-Python via segno, no image dependencies)."""

from __future__ import annotations

import io

import segno


def generate_qr_svg(data: str) -> str:
    buf = io.BytesIO()
    segno.make(data, error="m").save(buf, kind="svg", scale=4, border=2)
    return buf.getvalue().decode("utf-8")
