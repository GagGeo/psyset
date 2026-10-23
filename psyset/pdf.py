"""Page counts and PDF merge with duplex padding, written atomically."""
import os
import tempfile
from functools import lru_cache
from pathlib import Path

from pypdf import PdfReader, PdfWriter


class PdfReadError(Exception):
    def __init__(self, path, reason: str = ""):
        self.path = Path(path)
        self.reason = reason
        super().__init__(f"{self.path.name}: {reason}" if reason else self.path.name)


def _open(path: Path) -> PdfReader:
    """Open a PDF (empty-password decrypt for owner-locked files); any failure -> PdfReadError."""
    try:
        reader = PdfReader(path)
        if reader.is_encrypted and not reader.decrypt(""):
            raise ValueError("password protected")
        len(reader.pages)  # force the page tree to parse now
        return reader
    except Exception as e:
        raise PdfReadError(path, str(e) or type(e).__name__) from e


@lru_cache(maxsize=2048)
def _count(path: str, mtime_ns: int) -> int:
    return len(_open(Path(path)).pages)


def page_count(path: Path) -> int:
    path = Path(path)
    try:
        mtime_ns = path.stat().st_mtime_ns
    except OSError as e:
        raise PdfReadError(path, str(e)) from e
    return _count(str(path), mtime_ns)


def merge(pdfs: list[Path], out: Path, duplex: bool) -> int:
    """Concatenate `pdfs` into `out` (all-or-nothing); with duplex, odd documents get a blank page."""
    out = Path(out)
    writer = PdfWriter()
    for path in pdfs:
        pages = _open(Path(path)).pages
        for page in pages:
            writer.add_page(page)
        if duplex and len(pages) % 2:
            box = pages[-1].mediabox
            writer.add_blank_page(float(box.width), float(box.height))
    tmp = tempfile.NamedTemporaryFile(dir=out.parent, suffix=".pdf", delete=False)
    try:
        with tmp:
            writer.write(tmp)
        os.replace(tmp.name, out)
    except BaseException:
        Path(tmp.name).unlink(missing_ok=True)
        raise
    return len(writer.pages)


def estimate(docs: list[Path], duplex: bool) -> tuple[int, int]:
    """(pages incl. duplex padding over the PDFs, number of non-PDF documents)."""
    pages = others = 0
    for d in docs:
        if Path(d).suffix.lower() != ".pdf":
            others += 1
            continue
        n = page_count(d)
        pages += n + (n % 2 if duplex else 0)
    return pages, others
