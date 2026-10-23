"""Scan the tests library: domain/test folders -> Instrument records."""
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

SUPPORTED = {".pdf", ".doc", ".docx", ".odt"}
INFO_FILE = "psyset.json"
SYSTEM_FILES = {"thumbs.db", "desktop.ini", "icon\r"}  # OS clutter: neither a role nor unclassified
_ROLE = re.compile(r"(test|rating)(?:-(.+))?", re.I)


class LibraryMissing(Exception):
    pass


def natural_key(s: str) -> list:
    """Sort key: digit runs compare as numbers and come before letters ("2" < "10" < "A")."""
    return [(0, int(p)) if p.isdecimal() else (1, p)
            for p in re.split(r"(\d+)", s.casefold()) if p]


@dataclass
class Instrument:  # not "Test*": pytest would try to collect it
    folder: Path
    domain: str
    name: str
    reference: str = ""
    subdomain: str = ""
    has_info: bool = False
    sheets: dict[str, Path] = field(default_factory=dict)  # label -> path; "" = unlabelled
    crfs: dict[str, Path] = field(default_factory=dict)
    instructions: list[Path] = field(default_factory=list)
    norms: list[Path] = field(default_factory=list)
    unclassified: list[Path] = field(default_factory=list)
    unsupported: list[Path] = field(default_factory=list)  # sheet/crf role, format not in SUPPORTED
    duplicates: list[Path] = field(default_factory=list)  # same role+label, losing file (PDF wins)

    def versions(self) -> list[str]:
        labels = {k for k in (*self.sheets, *self.crfs) if k}
        return sorted(labels, key=natural_key)

    def key(self, root: Path) -> str:
        return self.folder.relative_to(root).as_posix()


def read_info(folder: Path) -> dict | None:
    try:
        data = json.loads((folder / INFO_FILE).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def write_info(folder: Path, name: str, reference: str, subdomain: str) -> None:
    data = {"name": name, "reference": reference, "subdomain": subdomain}
    (folder / INFO_FILE).write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _subdirs(path: Path) -> list[Path]:
    return sorted((p for p in path.iterdir() if p.is_dir() and not p.name.startswith(".")),
                  key=lambda p: p.name)


def _readable_subdirs(path: Path) -> list[Path]:
    """Subfolders of a domain; an unreadable one (System Volume Information…) has none."""
    try:
        return _subdirs(path)
    except OSError:
        return []


def list_domains(root: Path) -> list[str]:
    if not root.is_dir():
        raise LibraryMissing(str(root))
    return [p.name for p in _subdirs(root)]


def _scan_test(folder: Path, domain: str) -> Instrument | None:
    """None if the folder cannot be read: it is skipped, the rest of the library still loads."""
    try:
        files = sorted((f for f in folder.iterdir() if f.is_file()), key=lambda p: p.name)
    except OSError:
        return None
    info = read_info(folder)
    inst = Instrument(folder=folder, domain=domain, name=folder.name, has_info=info is not None)
    if info:
        text = lambda k: v if isinstance(v := info.get(k), str) else ""  # non-strings = absent
        inst.name = text("name") or folder.name
        inst.reference = text("reference")
        inst.subdomain = text("subdomain")
    for f in files:
        if (f.name.startswith((".", "~$")) or f.name == INFO_FILE
                or f.name.casefold() in SYSTEM_FILES):
            continue
        stem, ext = f.stem.casefold(), f.suffix.lower()
        m = _ROLE.fullmatch(f.stem)
        if m:
            if ext not in SUPPORTED:
                inst.unsupported.append(f)
                continue
            slots = inst.sheets if m.group(1).lower() == "test" else inst.crfs
            label = m.group(2) or ""
            old = slots.get(label)
            if old is None:
                slots[label] = f
            elif ext == ".pdf" and old.suffix.lower() != ".pdf":
                inst.duplicates.append(old)
                slots[label] = f
            else:
                inst.duplicates.append(f)
        elif stem.startswith("instruction"):
            inst.instructions.append(f)
        elif stem.startswith("norm"):
            inst.norms.append(f)
        else:
            inst.unclassified.append(f)
    return inst


def scan_library(root: Path) -> list[Instrument]:
    if not root.is_dir():
        raise LibraryMissing(str(root))
    found = [i for d in _subdirs(root) for t in _readable_subdirs(d)
             if (i := _scan_test(t, d.name))]
    found.sort(key=lambda i: (i.domain.casefold(), i.subdomain == "",
                              i.subdomain.casefold(), i.name.casefold()))
    return found
