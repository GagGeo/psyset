"""Word / LibreOffice conversion to PDF, and the all-or-nothing generate pipeline."""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from .pdf import PdfReadError, merge

TIMEOUT = 120  # seconds per file; a converter stuck on a dialog fails instead of hanging

MAC_WORD = Path("/Applications/Microsoft Word.app")
MAC_WORD_TMP = Path.home() / "Library/Containers/com.microsoft.Word/Data/tmp/psyset"
SOFFICE_PATHS = (
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
    r"C:\Program Files\LibreOffice\program\soffice.exe",
)

# Paths arrive as argv, never interpolated into the script (spaces, accents, quotes).
APPLESCRIPT = """\
on run argv
    set srcPath to item 1 of argv
    set outPath to item 2 of argv
    tell application "Microsoft Word"
        set theDoc to open file name srcPath read only true
        try
            save as theDoc file name outPath file format format PDF
        on error errMsg
            close theDoc saving no
            error errMsg
        end try
        close theDoc saving no
    end tell
end run
"""

# Paths arrive through environment variables, never interpolated into the command.
POWERSHELL = """\
$ErrorActionPreference = 'Stop'
$w = New-Object -ComObject Word.Application
$w.Visible = $false
$w.DisplayAlerts = 0
try {
    $src = $env:PSYSET_SRC
    $out = $env:PSYSET_OUT
    $d = $w.Documents.Open($src, $false, $true)
    $d.SaveAs([ref]$out, [ref]17)
    $d.Close(0)
} finally {
    $w.Quit()
}
"""


class ConversionError(Exception):
    def __init__(self, path, reason: str = ""):
        self.path = Path(path)
        self.reason = reason
        super().__init__(f"{self.path.name}: {reason}" if reason else self.path.name)


class NoConverter(Exception):
    pass


class OutputError(Exception):
    """A destination (or its temp file) could not be written. `written`: destinations
    already replaced before the failure (empty when nothing was written)."""

    def __init__(self, path, reason: str = "", written=()):
        self.path = Path(path)
        self.reason = reason
        self.written = list(written)
        super().__init__(f"{self.path.name}: {reason}" if reason else self.path.name)


def _word_installed() -> bool:
    if sys.platform == "darwin":
        return MAC_WORD.exists()
    if sys.platform == "win32":
        import winreg

        try:
            winreg.CloseKey(winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, "Word.Application"))
            return True
        except OSError:
            return False
    return False


def _soffice() -> str | None:
    return shutil.which("soffice") or next((p for p in SOFFICE_PATHS if Path(p).exists()), None)


def find_converters() -> list[str]:
    found = []
    if _word_installed():
        found.append("word")
    if _soffice():
        found.append("libreoffice")
    return found


def _run(cmd, **kw):
    if os.name == "nt":  # no console window flashing up for each conversion
        kw["creationflags"] = subprocess.CREATE_NO_WINDOW
    # errors="replace": stderr may come in an OEM code page; stdin: a prompt fails, never waits
    return subprocess.run(cmd, timeout=TIMEOUT, check=True, capture_output=True, text=True,
                          errors="replace", stdin=subprocess.DEVNULL, **kw)


def _word(src: Path, out_dir: Path) -> Path:
    out = out_dir / f"{src.stem}.pdf"
    if sys.platform == "win32":
        env = {**os.environ, "PSYSET_SRC": str(src.resolve()), "PSYSET_OUT": str(out.resolve())}
        _run(["powershell", "-NoProfile", "-NonInteractive", "-Command", POWERSHELL], env=env)
        return out
    # Word is sandboxed: let it write inside its own container, then move the result out.
    MAC_WORD_TMP.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(dir=MAC_WORD_TMP))
    try:
        # Word never sees the caller's file: it opens a private copy inside its container.
        copy = Path(shutil.copy2(src, work / src.name))
        produced = work / out.name
        _run(["osascript", "-e", APPLESCRIPT, str(copy), str(produced)])
        if produced.exists():
            shutil.move(produced, out)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return out


def _libreoffice(src: Path, out_dir: Path) -> Path:
    _run([_soffice() or "soffice", "--headless", "--convert-to", "pdf", "--outdir", str(out_dir), str(src)])
    return out_dir / f"{src.stem}.pdf"


_CONVERTERS = {"word": _word, "libreoffice": _libreoffice}


def to_pdf(src: Path, out_dir: Path, converters: list[str] | None = None) -> Path:
    """Convert a private copy of `src` to a PDF inside `out_dir`; the original is never opened."""
    src, out_dir = Path(src), Path(out_dir)
    converters = find_converters() if converters is None else converters
    if not converters:
        raise NoConverter("Neither Microsoft Word nor LibreOffice was found")
    reason = ""
    # An app that already has `src` open (maybe with unsaved edits) must not get it back to close.
    with tempfile.TemporaryDirectory() as work:
        try:
            copy = Path(shutil.copy2(src, Path(work) / src.name))
        except OSError as e:
            raise ConversionError(src, str(e)) from e
        for name in converters:
            try:
                out = _CONVERTERS[name](copy, out_dir)
                if out.exists():
                    return out
                reason = f"{name}: no PDF was produced"
            except subprocess.TimeoutExpired:
                reason = f"{name}: timed out after {TIMEOUT} s"
            except subprocess.CalledProcessError as e:
                reason = f"{name}: {(e.stderr or '').strip() or e}"
            except OSError as e:
                reason = f"{name}: {e}"
    raise ConversionError(src, reason)


def generate(jobs: dict[Path, list[Path]], duplex: bool, convert=to_pdf) -> dict[Path, int]:
    """Write each destination from its ordered source docs, or write nothing at all.

    Every distinct non-PDF is converted once, every job is merged to a temp file next to
    its destination, and only when all succeeded are the temp files moved into place.
    """
    temps: list[Path] = []
    try:
        with tempfile.TemporaryDirectory() as tmp:
            converted: dict[Path, Path] = {}
            for docs in jobs.values():
                for doc in docs:
                    if Path(doc).suffix.lower() != ".pdf" and doc not in converted:
                        out_dir = Path(tmp) / str(len(converted))
                        out_dir.mkdir()
                        converted[doc] = convert(doc, out_dir)
            source_of = {pdf: doc for doc, pdf in converted.items()}
            pages: dict[Path, int] = {}
            tmp_of: dict[Path, Path] = {}
            for dest, docs in jobs.items():
                try:
                    fd, name = tempfile.mkstemp(dir=Path(dest).parent, suffix=".pdf")
                    os.close(fd)
                    temps.append(Path(name))
                    tmp_of[dest] = Path(name)
                    pages[dest] = merge([converted.get(d, d) for d in docs], Path(name), duplex)
                except PdfReadError as e:  # name the user's document, not our temp PDF
                    if e.path in source_of:
                        raise PdfReadError(source_of[e.path], e.reason) from e
                    raise
                except OSError as e:
                    raise OutputError(dest, str(e)) from e
        written: list[Path] = []
        for dest, name in tmp_of.items():
            try:
                os.replace(name, dest)
            except OSError as e:
                raise OutputError(dest, str(e), written) from e
            written.append(dest)
        return pages
    finally:
        for name in temps:
            name.unlink(missing_ok=True)
