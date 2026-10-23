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
from psyset.library import parse_role, read_info, write_info

ROLES = ("test", "rating", "instructions", "norms")
_BAD_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f\x7f]')
_RESERVED = {"CON", "PRN", "AUX", "NUL",
             *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}


class InvalidName(ValueError):
    pass


class AlreadyExists(Exception):  # not "Test*": pytest would try to collect it
    pass


class FolderBusy(Exception):
    """The test folder could not be renamed or moved (a file inside is open?). Nothing was
    copied or deleted; `path` is where the folder is now."""

    def __init__(self, path: Path, reason: str = ""):
        self.path, self.reason = Path(path), reason
        super().__init__(f"{self.path}: {reason}" if reason else str(self.path))


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


def holds_role(f: Path, role: str, label: str = "") -> bool:
    """Does file `f` hold `role` (+ sanitized `label`), any extension? put_file replaces such files."""
    found = parse_role(f.stem)
    if not found or found[0] != role:
        return False
    return role not in ("test", "rating") or _key(found[1]) == _key(label)


def _matching(folder: Path, role: str, label: str) -> list[Path]:
    """Files already holding `role` (+ `label`) in `folder`, any extension."""
    return [f for f in folder.iterdir() if f.is_file() and holds_role(f, role, label)]


def _clean_label(label: str) -> str:
    return sanitize_folder_name(label) if label.strip() else ""


def _target_name(folder: Path, role: str, label: str, ext: str) -> str:
    """Standard file name, test name first: cvlt-test.pdf, cvlt-rating-A.pdf, cvlt-norms-2.jpg."""
    if role not in ROLES:
        raise ValueError(f"unknown role: {role}")
    prefix = folder.name.casefold().replace(" ", "-") + "-"
    if role == "norms":  # never replaces: first free norms, norms-2, ...
        taken = {_key(f.stem) for f in folder.iterdir()}
        n = 1
        while _key(stem := prefix + ("norms" if n == 1 else f"norms-{n}")) in taken:
            n += 1
        return stem + ext
    if role == "instructions":
        return prefix + "instructions" + ext
    return prefix + (f"{role}-{label}" if label else role) + ext


def put_file(folder: Path, role: str, src: Path, label: str = "",
             replaces: Path | None = None) -> Path:
    """Copy `src` in as `role`. test/rating: files of that role + label go to the Trash.
    instructions: only `replaces` does; any other file already at the target name is
    refused (AlreadyExists), never overwritten. norms: never replaces anything."""
    label = _clean_label(label)
    name = _target_name(folder, role, label, src.suffix.lower())
    dest = folder / name
    if role == "instructions" and _find_entry(folder, name, exclude=replaces):
        raise AlreadyExists(name)
    tmp = folder / f".psyset-{uuid.uuid4().hex}.tmp"  # a copy, not an original: hidden is fine
    try:
        shutil.copy2(src, tmp)  # copy first: a failed copy must not cost the old file
        if role == "instructions":
            old = [replaces] if replaces and replaces.exists() else []
        else:
            old = _matching(folder, role, label) if role != "norms" else []
        for f in old:
            send2trash.send2trash(str(f))
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
    if str(target) != str(folder):  # not Path !=: WindowsPath equality ignores case ("TMT" -> "tmt")
        new_domain = not dom.exists()
        dom.mkdir(parents=True, exist_ok=True)
        try:
            _rename_folder(folder, target)
        except FolderBusy:
            if new_domain:
                try:
                    dom.rmdir()
                except OSError:
                    pass
            raise
    write_info(target, name.strip(), reference, subdomain)
    return target


def _rename_folder(folder: Path, target: Path) -> None:
    """Rename only (one library volume): never shutil.move, whose copy + delete fallback
    would permanently delete files when Windows refuses to rename a folder in use."""
    if target.parent != folder.parent or _key(folder.name) != _key(target.name):
        try:
            os.rename(folder, target)
        except OSError as e:
            raise FolderBusy(folder, e.strerror or str(e)) from e
        return
    # case-only rename, in two steps for case-insensitive filesystems; the temp name is
    # visible and keeps psyset.json, so a crash never hides the test
    tmp = folder.with_name(f"psyset-renaming-{uuid.uuid4().hex[:8]}-{folder.name}")
    try:
        os.rename(folder, tmp)
    except OSError as e:
        raise FolderBusy(folder, e.strerror or str(e)) from e
    try:
        os.rename(tmp, target)
    except OSError as e:
        try:
            os.rename(tmp, folder)
            where = folder
        except OSError:
            where = tmp
        raise FolderBusy(where, e.strerror or str(e)) from e


def assign_role(path: Path, role: str, label: str = "") -> Path:
    target = path.parent / _target_name(path.parent, role, _clean_label(label), path.suffix.lower())
    if _find_entry(path.parent, target.name, exclude=path):
        raise AlreadyExists(target.name)
    if str(target) != str(path):  # WindowsPath equality ignores case
        os.rename(path, target)
    return target


def remove_test(folder: Path) -> None:
    send2trash.send2trash(str(folder))


def remove_file(path: Path) -> None:
    send2trash.send2trash(str(path))


def create_starter_library(root: Path, lang: str) -> None:
    for d in DOMAINS[lang]:
        (root / d).mkdir(parents=True, exist_ok=True)
