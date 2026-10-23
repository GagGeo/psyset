from pathlib import Path

import pytest
from pypdf import PdfWriter


def pdf(path, pages=1, width=595, height=842) -> Path:
    """Write a PDF of `pages` blank pages; creates parent dirs."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    w = PdfWriter()
    for _ in range(pages):
        w.add_blank_page(width, height)
    with path.open("wb") as f:
        w.write(f)
    return path


@pytest.fixture
def make_lib(tmp_path):
    """make({domain: {test: [filenames]}}) -> library root under tmp_path."""

    def make(spec: dict[str, dict[str, list[str]]]) -> Path:
        root = tmp_path / "lib"
        root.mkdir(exist_ok=True)
        for domain, tests in spec.items():
            for test, files in tests.items():
                folder = root / domain / test
                folder.mkdir(parents=True, exist_ok=True)
                for name in files:
                    if name.lower().endswith(".pdf"):
                        pdf(folder / name)
                    else:
                        (folder / name).write_bytes(b"placeholder")
        return root

    return make
