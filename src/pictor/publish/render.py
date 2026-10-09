"""HTML to PNG through a headless browser, fully offline.

The page handed in is self-contained (fonts and images inlined), so the only
thing the browser needs is a path to it. Chrome is found through
`$PICTOR_CHROME`, then the usual install locations -- including, under WSL,
the Windows install, which needs its paths in Windows form.
"""

from __future__ import annotations

import os
import shutil
import struct
import subprocess
from pathlib import Path

ENV = "PICTOR_CHROME"
CANDIDATES = (
    "google-chrome",
    "chromium",
    "chromium-browser",
    "/mnt/c/Program Files/Google/Chrome/Application/chrome.exe",
    "/mnt/c/Program Files (x86)/Google/Chrome/Application/chrome.exe",
)


class RenderError(RuntimeError):
    pass


def find_chrome() -> str:
    for candidate in ([os.environ[ENV]] if os.environ.get(ENV) else []) + list(CANDIDATES):
        found = shutil.which(candidate) or (candidate if Path(candidate).is_file() else None)
        if found:
            return found
    raise RenderError(f"no headless Chrome found; set ${ENV}")


def _for(chrome: str, path: Path) -> str:
    """A path as this browser will understand it."""
    if chrome.endswith(".exe"):
        return subprocess.check_output(["wslpath", "-w", str(path)], text=True).strip()
    return str(path)


def png_size(path: Path) -> tuple[int, int]:
    with open(path, "rb") as fh:
        head = fh.read(24)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        raise RenderError(f"{path} is not a PNG")
    return struct.unpack(">II", head[16:24])


def screenshot(html: Path, png: Path, size: tuple[int, int]) -> None:
    chrome = find_chrome()
    if chrome.endswith(".exe"):
        # A WSL path reaches Windows as a UNC path, \\wsl.localhost\..., and its
        # leading slashes are part of it: file:///// + //wsl.localhost/...
        url = "file:///" + _for(chrome, html.resolve()).replace("\\", "/")
    else:
        url = html.resolve().as_uri()
    png.unlink(missing_ok=True)
    subprocess.run(
        [chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
         "--force-device-scale-factor=1", f"--window-size={size[0]},{size[1]}",
         "--virtual-time-budget=4000", f"--screenshot={_for(chrome, png.resolve())}", url],
        capture_output=True, timeout=120,
    )
    if not png.is_file():
        raise RenderError(f"the browser wrote no screenshot for {html}")
    if png_size(png) != size:
        raise RenderError(f"{png} is {png_size(png)}, expected {size}")
