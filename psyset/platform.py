"""OS helpers: open a file/folder, reveal it in Finder/Explorer, locate bundled assets."""
import os
import subprocess
import sys
from pathlib import Path


def open_path(p: Path) -> None:
    if os.name == "nt":
        os.startfile(str(p))  # noqa: Windows only
    elif sys.platform == "darwin":
        subprocess.run(["open", str(p)], check=False)
    else:
        subprocess.run(["xdg-open", str(p)], check=False)


def reveal_path(p: Path) -> None:
    if os.name == "nt":
        subprocess.run(["explorer", "/select,", str(p)], check=False)
    elif sys.platform == "darwin":
        subprocess.run(["open", "-R", str(p)], check=False)
    else:
        open_path(p.parent)


def asset_path(*parts) -> Path | None:
    """`<bundle or repo root>/assets/<parts>`, or None if absent."""
    bases = []
    if hasattr(sys, "_MEIPASS"):
        bases.append(Path(sys._MEIPASS))
    bases.append(Path(__file__).resolve().parent.parent)
    for base in bases:
        p = base.joinpath("assets", *parts)
        if p.exists():
            return p
    return None
