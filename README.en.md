🇫🇷 [Version française](README.md)

<p align="center">
  <img src="assets/logo/psyset-lockup.svg" alt="PsySet" width="360">
</p>

# PsySet — put together a neuropsychological exam in a minute

A small app (Mac and PC, FR/EN interface) for neuropsychologists: tick the
tests you chose for the patient, put them in order, and PsySet builds the
print-ready PDFs — patient sheets, CRFs, or everything merged. It reads
**your own** tests folder, as it is on your computer. **100% local: no data
ever leaves your computer.**

<!-- TODO: add assets/screenshots/psyset-fr.png -->

## Why use it?

For every patient, the same ritual: open the tests folder, go domain by
domain, open the right files, print the patient's sheet and the CRF of each
test… and forget a sheet along the way. PsySet replaces all that with a
checklist. Next to each test, small tags show at a glance what it contains:
`SHEET · CRF · INSTR · NORMS` (a crossed-out tag = missing file).

## Organise your tests library

PsySet reads your folder tree: the tree is the master copy, and you can keep
browsing it in Finder or Explorer. One folder per domain, one subfolder per
test:

```
Tests library/
├── Executive functioning/         ← domain
│   ├── TMT/                       ← test
│   │   ├── psyset.json            ← test info (written by the app)
│   │   ├── test.pdf               ← patient sheet
│   │   ├── rating.pdf             ← CRF (the clinician's scoring form)
│   │   └── instructions.pdf       ← administration instructions
│   └── Hayling/
│       ├── rating.pdf
│       ├── instructions.docx
│       ├── norms.pdf              ← norms
│       └── norm-calculation.xlsx  ← also counted as norms
└── Memory/
    └── CVLT/
        ├── test-A.pdf             ← version A: patient sheet…
        ├── rating-A.pdf           ←   …and its CRF
        ├── test-B.pdf             ← version B
        └── rating-B.docx
```

The four roles are recognised from the file name:

| File | Role | Tag |
|---|---|---|
| `test` | patient sheet | `SHEET` |
| `rating` | CRF | `CRF` |
| `instructions` | instructions | `INSTR` |
| anything starting with `norm` (`norms.pdf`, `norm-calculation.xlsx`…) | norms (one or several files) | `NORMS` |

- **Versions**: `test-A.pdf` and `rating-A.pdf` belong together (parallel
  forms A/B, or one sheet per subtest). An unlabelled file (`test.pdf`) is
  shared by all versions.
- Patient sheets and CRFs can be **PDF, Word (`.doc`, `.docx`) or `.odt`**.
- A test folder laid out differently, or files with unusual names, still show
  up: unclassified files are greyed out, and one click lets you assign them a
  role (the file is then renamed).

No library yet? At first launch, PsySet can **create an empty one** with the
recommended domains: Executive functioning, Memory, Instrumental functioning,
Attention, Social cognition, Autonomy, Mood.

## Installation

Download the zip of the latest version from the
**[Releases](../../releases/latest)** tab.

**On Mac** (`PsySet-macOS.zip`)
1. Unzip, then drag `PsySet.app` wherever you like (Applications, Desktop…).
2. First launch only: **right-click the app → "Open" → "Open"**.
   (The app is not Apple-signed; a normal double-click would be blocked.)

**On Windows** (`PsySet-Windows.zip`)
1. Unzip, then double-click `PsySet.exe`.
2. If the blue "Windows protected your PC" screen appears:
   *More info* → *Run anyway* (first launch only).

At first launch, pick the language, then **your existing tests folder** or
**create an empty library**. You can change the folder later from the
settings (top right).

### Word or LibreOffice

To merge sheets or CRFs that are Word/ODT files, PsySet has to convert them to
PDF, so you need **Microsoft Word or LibreOffice** installed (nothing to
install if all your documents are already PDFs). Your original files are never
modified: conversion works on temporary copies.

On a Mac with Word, the first conversion triggers a one-time macOS prompt:
**"PsySet wants to control Microsoft Word"**. Click OK (the first time, PsySet warns you just
before). If a file can't be converted, generation stops and names it: never a
PDF with a silent gap.

## Usage

1. **Tick** the tests in the middle list (pick a domain on the left, or search
   by name, subdomain or author across the whole library). Clicking a tag opens
   the matching file.
2. **Order** the exam in the right-hand panel: drag and drop, or the ▲ ▼
   arrows; ✕ removes a test.
3. **Versions**: if a test has several, `[A] [B]` chips on its row let you
   choose A, B, or A+B.
4. **Generate**: tick what you need — *Patient sheets*, *CRFs*, *Everything
   merged* ("test by test" or "sheets, then CRFs") — then **Generate PDFs…**.
   Suggested names look like `2026-10-23_patient-sheets.pdf` (never a patient
   name).
5. **Double-sided**: the option adds a blank page after any document with an
   odd page count, so each document starts on a fresh sheet.
6. A warning lists the tests that have no patient sheet or no CRF.

PsySet doesn't print: open the PDF and print it.

**Add or edit a test**: "＋ Add a test" (name, bibliographic reference,
domain, subdomain, and one file per role; several labelled files A, B… for
sheets and CRFs). Files are **copied** into the library under their standard
names; your originals stay where they are. "Edit info" reopens the form; "Remove
test" sends the folder to the **Trash / Recycle Bin**: nothing is ever
permanently deleted. Exception on Windows: a network or removable drive (USB
stick) often has no Recycle Bin, so "moving to the Recycle Bin" can be
permanent there.

## 100% local

No network access, no patient data: PsySet only handles your test files, on
your computer.

---

## For developers

Python/tkinter app: entry point [`PsySet.py`](PsySet.py), code in
[`psyset/`](psyset), logos and icons in [`assets/`](assets). Dependencies:
`pypdf`, `send2trash` and `cryptography` (publishers' protected PDFs).

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest -q
```

**Local build (macOS)**: `./build.sh` (PyInstaller) → `dist/PsySet.app`.

**Automated releases**: pushing a `v*` tag triggers GitHub Actions
([`.github/workflows/build.yml`](.github/workflows/build.yml)), which runs the
tests, builds the universal macOS `.app` and the Windows `.exe`, then
attaches them to the Release:

```bash
git tag v1.0.0 && git push origin v1.0.0
```

## License

[MIT](LICENSE) — free to use, modify and share.
