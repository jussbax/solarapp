"""PL Development brand for the PDFs: colours, Montserrat (bundled), logo mark."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image

ASSETS = Path(__file__).resolve().parent / "assets"
BLACK = colors.HexColor("#111111")
GOLD = colors.HexColor("#C9A227")
GOLD_DARK = colors.HexColor("#a4841c")
OFF_WHITE = colors.HexColor("#F5F5F3")
GRAY = colors.HexColor("#2D2D2D")
MUTED = colors.HexColor("#6b6b66")
LINE = colors.HexColor("#e2e2dc")
GOLD_BG = colors.HexColor("#faf4e1")
# chart colours validated for colour-blind separation on a light surface
C_GOLD, C_BLUE, C_ORANGE = "#C9A227", "#2f5fd8", "#c84f2b"

_registered: Optional[tuple[str, str, str]] = None


def fonts() -> tuple[str, str, str]:
    """(regular, semibold, bold) font names; Montserrat when the bundled files are present, else Helvetica."""
    global _registered
    if _registered:
        return _registered
    files = {"Montserrat": "Montserrat-400.ttf", "Montserrat-SemiBold": "Montserrat-600.ttf", "Montserrat-Bold": "Montserrat-700.ttf"}
    try:
        for name, fn in files.items():
            path = ASSETS / "fonts" / fn
            if not path.exists():
                raise FileNotFoundError(fn)
            if name not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont(name, str(path)))
        pdfmetrics.registerFontFamily("Montserrat", normal="Montserrat", bold="Montserrat-Bold", italic="Montserrat", boldItalic="Montserrat-Bold")
        _registered = ("Montserrat", "Montserrat-SemiBold", "Montserrat-Bold")
    except Exception:  # noqa: BLE001
        _registered = ("Helvetica", "Helvetica-Bold", "Helvetica-Bold")
    return _registered


def logo(height: float = 12 * mm) -> Optional[Image]:
    path = ASSETS / "logo-mark.png"
    if not path.exists():
        return None
    return Image(str(path), width=height, height=height)
