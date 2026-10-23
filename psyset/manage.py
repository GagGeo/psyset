"""Add / edit / assign / remove tests in the library. Originals are copied, never moved;
replacements and removals go to the Trash (send2trash), never deleted."""
import os
import re
import shutil
import unicodedata
import uuid
from pathlib import Path

import send2trash

from psyset.i18n import DOMAINS
from psyset.library import _ROLE, read_info, write_info

ROLES = ("test", "rating", "instructions", "norms")
_BAD_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f\x7f]')
_RESERVED = {"CON", "PRN", "AUX", "NUL",
             *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}


class InvalidName(ValueError):
    pass


class AlreadyExists(Exception):  # not "Test*": pytest would try to collect it
    pass


def sanitize_folder_name(name: str) -> str:
    s = _BAD_CHARS.sub("-", name).strip().strip(". ")  # leading dots would hide it from the scan
    if not s:
        raise InvalidName(name)
    if s.split(".")[0].rstrip().upper() in _RESERVED:
        s += "_"
    return s


def _key(name: str) -> str:
    """Comparison key: macOS may store the same accented name as NFC or NFD."""
    return unicodedata.normalize("NFC", name).casefold()


def _find_entry(parent: Path, name: str, exclude: Path | None = None) -> Path | None:
    """Existing entry of `parent` whose name equals `name` ignoring case (`exclude` skipped)."""
    if not parent.is_dir():
        return None
    return next((p for p in parent.iterdir()
                 if _key(p.name) == _key(name) and p != exclude), None)


def _labels(items: list[tuple[str, Path]]) -> list[tuple[str, Path]]:
    """One item: unlabelled. Several: each needs a non-empty, unique (case-insensitive) label."""
    if len(items) <= 1:
        return [("", src) for _, src in items]
    out, seen = [], set()
    for label, src in items:
        label = sanitize_folder_name(label)  # empty -> InvalidName
        if _key(label) in seen:
            raise InvalidName(f"duplicate label: {label}")
        seen.add(_key(label))
        out.append((label, src))
    return out


def _matching(folder: Path, role: str, label: str) -> list[Path]:
    """Files already holding `role` (+ `label`) in `folder`, any extension."""
    found = []
    for f in folder.iterdir():
        if not f.is_file():
            continue
        if role in ("test", "rating"):
            m = _ROLE.fullmatch(f.stem)
            if m and m.group(1).lower() == role and _key(m.group(2) or "") == _key(label):
                found.append(f)
        elif _key(f.stem) == role:
            found.append(f)
    return found


def _clean_label(label: str) -> str:
    return sanitize_folder_name(label) if label.strip() else ""


def _target_name(folder: Path, role: str, label: str, ext: str) -> str:
    """Standard file name for `role` (+ sanitized `label`) in `folder`."""
    if role not in ROLES:
        raise ValueError(f"unknown role: {role}")
    if role == "norms":  # never replaces: first free norms, norms-2, ...
        taken = {_key(f.stem) for f in folder.iterdir()}
        n = 1
        while (stem := "norms" if n == 1 else f"norms-{n}") in taken:
            n += 1
        return stem + ext
    if role == "instructions":
        return "instructions" + ext
    return (f"{role}-{label}" if label else role) + ext


def put_file(folder: Path, role: str, src: Path, label: str = "") -> Path:
    label = _clean_label(label)
    name = _target_name(folder, role, label, src.suffix.lower())
    dest = folder / name
    tmp = folder / f".psyset-{uuid.uuid4().hex}.tmp"  # hidden: the scan ignores it
    try:
        shutil.copy2(src, tmp)  # copy first: a failed copy must not cost the old file
        if role != "norms":
            for old in _matching(folder, role, label):
                send2trash.send2trash(str(old))
        os.replace(tmp, dest)
    finally:
        tmp.unlink(missing_ok=True)
    return dest


def add_test(root: Path, domain: str, name: str, reference: str, subdomain: str,
             sheets: list[tuple[str, Path]], crfs: list[tuple[str, Path]],
             instructions: Path | None, norms: list[Path]) -> Path:
    folder_name = sanitize_folder_name(name)
    sheets, crfs = _labels(sheets), _labels(crfs)
    dom = _find_entry(root, sanitize_folder_name(domain)) or root / sanitize_folder_name(domain)
    if _find_entry(dom, folder_name):
        raise AlreadyExists(folder_name)
    new_domain = not dom.exists()
    folder = dom / folder_name
    made = False
    try:
        folder.mkdir(parents=True)
        made = True
        for role, items in (("test", sheets), ("rating", crfs)):
            for label, src in items:
                put_file(folder, role, src, label)
        if instructions:
            put_file(folder, "instructions", instructions)
        for src in norms:
            put_file(folder, "norms", src)
        write_info(folder, name.strip(), reference, subdomain)
    except BaseException:
        if made:  # remove only what this call created
            shutil.rmtree(folder, ignore_errors=True)
            if new_domain:
                try:
                    dom.rmdir()  # harmless failure if anything else is in it
                except OSError:
                    pass
        raise
    return folder


def update_info(folder: Path, root: Path, name: str, reference: str,
                subdomain: str, domain: str) -> Path:
    current = (read_info(folder) or {}).get("name")
    if name.strip() == (current if isinstance(current, str) and current else folder.name):
        folder_name = folder.name  # name unchanged: never rename the folder unasked
    else:
        folder_name = sanitize_folder_name(name)
    dom_name = sanitize_folder_name(domain)
    dom = folder.parent if _key(folder.parent.name) == _key(dom_name) else (
        _find_entry(root, dom_name) or root / dom_name)
    if _find_entry(dom, folder_name, exclude=folder):  # the folder itself is no clash ("TMT" -> "tmt")
        raise AlreadyExists(folder_name)
    target = dom / folder_name
    if target != folder:
        dom.mkdir(parents=True, exist_ok=True)
        if dom == folder.parent and _key(folder.name) == _key(folder_name):
            tmp = folder.with_name(f".psyset-{uuid.uuid4().hex}")  # case-only rename, safe on
            folder.rename(tmp)                                     # case-insensitive filesystems
            tmp.rename(target)
        else:
            shutil.move(str(folder), str(target))
    write_info(target, name.strip(), reference, subdomain)
    return target


def assign_role(path: Path, role: str, label: str = "") -> Path:
    target = path.parent / _target_name(path.parent, role, _clean_label(label), path.suffix.lower())
    if _find_entry(path.parent, target.name, exclude=path):
        raise AlreadyExists(target.name)
    if target != path:
        os.rename(path, target)
    return target


def remove_test(folder: Path) -> None:
    send2trash.send2trash(str(folder))


def remove_file(path: Path) -> None:
    send2trash.send2trash(str(path))


def create_starter_library(root: Path, lang: str) -> None:
    for d in DOMAINS[lang]:
        (root / d).mkdir(parents=True, exist_ok=True)
