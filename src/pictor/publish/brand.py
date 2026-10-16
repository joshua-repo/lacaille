"""A house style, loaded from a brand directory outside this package.

pictor renders; it does not own anyone's identity. The colours, type, fonts and
logo files live with the brand (for Bayswater, `~/repo/bayswater/brand/`), and
are read from its `brand.toml`:

    name = "..."
    footer = "Backtest on historical data. Not investment advice."
    gradient = ["#16324A 0%", "#3B5A70 62%", "#B05F3A 100%"]   # the signature hairline

    [color]   # bg ink sub accent muted rule grid panel treat base
    [type]    # head, body: family names
    [assets]  # lockup, mark: SVG paths relative to the brand directory

    [[font]]  # one per face used
    family = "Spectral"
    file = "fonts/Spectral-Medium.ttf"
    weight = 500
    style = "normal"

Fonts and SVGs are inlined into the page that gets rendered, so the artefact is
one self-contained file and no path has to survive a trip to a browser on
another filesystem (Windows Chrome reading a WSL path).
"""

from __future__ import annotations

import base64
import os
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

COLORS = ("bg", "ink", "sub", "accent", "muted", "rule", "grid", "panel", "treat", "base")
ENV = "BAYSWATER_BRAND"


class BrandError(ValueError):
    pass


@dataclass(frozen=True)
class Font:
    family: str
    path: Path
    weight: str
    style: str


@dataclass(frozen=True)
class Brand:
    root: Path
    name: str
    footer: str
    gradient: tuple[str, ...]
    color: dict[str, str]
    head: str
    body: str
    fonts: tuple[Font, ...]
    assets: dict[str, Path]

    def font_faces(self) -> str:
        """@font-face rules with the fonts embedded as data URIs."""
        rules = []
        for f in self.fonts:
            data = base64.b64encode(f.path.read_bytes()).decode()
            rules.append(
                f"@font-face{{font-family:'{f.family}';font-weight:{f.weight};font-style:{f.style};"
                f"src:url(data:font/ttf;base64,{data}) format('truetype')}}"
            )
        return "\n".join(rules)

    def svg(self, asset: str, height: int, uid: str) -> str:
        """One of the brand's SVGs, inline, at `height` px, with its ids made
        unique -- two copies of one gradient id on a page break each other."""
        text = self.assets[asset].read_text()
        text = re.sub(r"<\?xml[^>]*\?>", "", text)
        for old in set(re.findall(r'id="([^"]+)"', text)):
            text = text.replace(f'id="{old}"', f'id="{uid}-{old}"').replace(
                f"url(#{old})", f"url(#{uid}-{old})"
            )
        text = re.sub(r'(<svg\b[^>]*?)\swidth="[^"]*"', r"\1", text, count=1)
        text = re.sub(r'(<svg\b[^>]*?)\sheight="[^"]*"', rf'\1 height="{height}"', text, count=1)
        return text.strip()

    @property
    def gradient_css(self) -> str:
        """Stops as written ("#16324A 0%"), else spaced evenly."""
        n = max(len(self.gradient) - 1, 1)
        stops = [s if " " in s else f"{s} {round(i * 100 / n)}%" for i, s in enumerate(self.gradient)]
        return f"linear-gradient(90deg,{','.join(stops)})"


def default_root() -> Path | None:
    value = os.environ.get(ENV)
    return Path(value).expanduser() if value else None


def load_brand(root: Path | None = None) -> Brand:
    root = root or default_root()
    if root is None:
        raise BrandError(f"no brand directory: pass --brand or set ${ENV}")
    root = Path(root).expanduser().resolve()
    try:
        raw = tomllib.loads((root / "brand.toml").read_text())
    except FileNotFoundError:
        raise BrandError(f"{root}/brand.toml not found") from None

    color = raw.get("color", {})
    if missing := [c for c in COLORS if c not in color]:
        raise BrandError(f"brand.toml [color] lacks {missing}")
    fonts = tuple(
        Font(f["family"], root / f["file"], str(f.get("weight", 400)), f.get("style", "normal"))
        for f in raw.get("font", [])
    )
    assets = {k: root / v for k, v in raw.get("assets", {}).items()}
    for p in [*(f.path for f in fonts), *assets.values()]:
        if not p.is_file():
            raise BrandError(f"brand file missing: {p}")
    return Brand(
        root=root,
        name=raw.get("name", ""),
        footer=raw.get("footer", ""),
        gradient=tuple(raw.get("gradient", (color["ink"], color["accent"]))),
        color=dict(color),
        head=raw["type"]["head"],
        body=raw["type"]["body"],
        fonts=fonts,
        assets=assets,
    )
