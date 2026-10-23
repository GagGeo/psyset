"""Session ordering, missing-file report and default output names. Pure logic, no I/O."""
from datetime import date
from pathlib import Path

from psyset.library import Instrument, natural_key

Entry = tuple[Instrument, list[str]]  # chosen version labels ([] if the test has none)

_NAMES = {
    "en": {"sheets": "patient-sheets", "crfs": "crfs", "merged": "complete"},
    "fr": {"sheets": "feuilles-patient", "crfs": "crf", "merged": "complet"},
}


def _pick(files: dict[str, Path], versions: list[str]) -> list[Path]:
    """Unlabelled file first (once), then chosen labels in natural order; unknown labels skipped."""
    labels = sorted({v for v in versions if v and v in files}, key=natural_key)
    return [files[k] for k in ("", *labels) if k in files]


def sheets_for(inst: Instrument, versions: list[str]) -> list[Path]:
    return _pick(inst.sheets, versions)


def crfs_for(inst: Instrument, versions: list[str]) -> list[Path]:
    return _pick(inst.crfs, versions)


def plan_outputs(session: list[Entry], merge_mode: str) -> dict[str, list[Path]]:
    sheets = [p for i, v in session for p in sheets_for(i, v)]
    crfs = [p for i, v in session for p in crfs_for(i, v)]
    if merge_mode == "sheets_first":
        merged = sheets + crfs
    else:  # "by_test"
        merged = [p for i, v in session for p in (*sheets_for(i, v), *crfs_for(i, v))]
    return {"sheets": sheets, "crfs": crfs, "merged": merged}


def missing(session: list[Entry]) -> dict[str, list[str]]:
    return {
        "no_sheet": [i.name for i, v in session if not sheets_for(i, v)],
        "no_crf": [i.name for i, v in session if not crfs_for(i, v)],
    }


def default_filename(kind: str, lang: str, day: date) -> str:
    return f"{day.isoformat()}_{_NAMES[lang][kind]}.pdf"


def default_versions(inst: Instrument, remembered: list[str] | None) -> list[str]:
    labels = inst.versions()
    if not labels:
        return []
    kept = [v for v in labels if v in (remembered or [])]
    return kept or labels[:1]
