import sys
from pathlib import Path

import pytest

from psyset.convert import ConversionError, NoConverter, OutputError
from psyset.library import Instrument
from psyset.pdf import PdfReadError
from psyset.ui.session_pane import (build_jobs, count_text, error_text, kinds_to_save,
                                    in_library, needs_word_prompt, reorder, toggle_version,
                                    warning_lines)


def test_reorder_moves_down_and_up():
    items = ["a", "b", "c", "d"]
    assert reorder(items, 0, 3) == ["b", "c", "a", "d"]   # insertion line above "d"
    assert reorder(items, 0, 4) == ["b", "c", "d", "a"]   # line after the last row
    assert reorder(items, 3, 0) == ["d", "a", "b", "c"]
    assert reorder(items, 1, 1) == items and reorder(items, 1, 2) == items  # dropped in place
    assert items == ["a", "b", "c", "d"]  # input untouched


def test_toggle_version_keeps_at_least_one():
    labels = ["A", "B", "10", "2"]
    assert toggle_version(["A"], "B", labels) == ["A", "B"]
    assert toggle_version(["A", "B"], "A", labels) == ["B"]
    assert toggle_version(["B"], "B", labels) == ["B"]          # last one stays on
    assert toggle_version(["10"], "2", labels) == ["2", "10"]   # natural order
    assert toggle_version(["A"], "Z", labels) == ["A"]          # unknown label ignored


def test_count_text_plurals_and_word():
    assert count_text("en", 1, 4, 0) == "(1 test · 4 p.)"
    assert count_text("en", 2, 6, 0) == "(2 tests · 6 p.)"
    assert count_text("fr", 2, 4, 1) == "(2 tests · 4 p. + 1 Word)"
    assert count_text("en", 1, 0, 2) == "(1 test · 2 Word)"
    assert count_text("en", 1, None, 0) == "(1 test · ? p.)"   # unreadable PDF
    assert count_text("en", 0, 0, 0) == ""


def _inst(tmp_path, name, sheets=(), crfs=(), unsupported=()):
    folder = tmp_path / name
    return Instrument(folder=folder, domain="d", name=name,
                      sheets={k: folder / f"test-{k}.pdf" for k in sheets},
                      crfs={k: folder / f"rating-{k}.pdf" for k in crfs},
                      unsupported=[folder / f for f in unsupported])


def test_warning_lines(tmp_path):
    tmt = _inst(tmp_path, "TMT", sheets=[""], crfs=[""])
    cvlt = _inst(tmp_path, "CVLT", sheets=[""], unsupported=["rating.xlsx"])
    hay = _inst(tmp_path, "Hayling", crfs=[""])
    assert warning_lines("en", [(tmt, []), (cvlt, []), (hay, [])]) == [
        "No patient sheet for: Hayling",
        "No CRF for: CVLT",
        "CVLT/rating.xlsx: unsupported format — skipped",
    ]
    assert warning_lines("fr", [(tmt, [])]) == []
    assert warning_lines("fr", [(hay, []), (cvlt, [])])[0] == "Aucune feuille patient pour : Hayling"


def test_kinds_to_save_skips_unticked_and_empty():
    plan = {"sheets": [], "crfs": [Path("r.pdf")], "merged": [Path("r.pdf")]}
    assert kinds_to_save(plan, {"sheets": True, "crfs": True, "merged": True}) == ["crfs", "merged"]
    assert kinds_to_save(plan, {"sheets": True, "crfs": False, "merged": False}) == []
    assert kinds_to_save({"sheets": [], "crfs": [], "merged": []},
                         {"sheets": True, "crfs": True, "merged": True}) == []


def test_build_jobs_and_duplicate_destination(tmp_path):
    plan = {"sheets": [Path("t.pdf")], "crfs": [Path("r.pdf")], "merged": [Path("t.pdf"), Path("r.pdf")]}
    a, b = tmp_path / "a.pdf", tmp_path / "b.pdf"
    assert build_jobs(plan, {"sheets": a, "merged": b}) == {a: [Path("t.pdf")],
                                                           b: [Path("t.pdf"), Path("r.pdf")]}
    with pytest.raises(ValueError) as e:
        build_jobs(plan, {"sheets": a, "crfs": tmp_path / "x" / ".." / "a.pdf"})
    assert e.value.args[0] == a


def test_needs_word_prompt(tmp_path):
    pdf_only = {tmp_path / "o.pdf": [Path("t.pdf")]}
    word = {tmp_path / "o.pdf": [Path("t.pdf"), Path("r.docx")]}
    has_word = lambda: ["word"]
    assert needs_word_prompt(word, {}, "darwin", has_word)
    assert not needs_word_prompt(word, {"word_prompt_explained": True}, "darwin", has_word)
    assert not needs_word_prompt(pdf_only, {}, "darwin", has_word)
    assert not needs_word_prompt(word, {}, "win32", has_word)
    assert not needs_word_prompt(word, {}, "darwin", lambda: ["libreoffice"])


def test_error_text_names_the_file(tmp_path):
    lib = tmp_path / "lib"
    rating = lib / "exec" / "tmt" / "rating.pdf"
    jobs = {tmp_path / "out.pdf": [lib / "a" / "t.pdf", lib / "mem" / "cvlt" / "rating.docx"]}
    msg = error_text("en", PdfReadError(rating, "EOF marker not found"), jobs, lib)
    assert "exec/tmt/rating.pdf" in msg and "EOF marker not found" in msg
    assert "Nothing was written" in msg
    msg = error_text("fr", ConversionError(lib / "mem" / "cvlt" / "rating.docx", "timeout"), jobs, lib)
    assert "mem/cvlt/rating.docx" in msg and "timeout" in msg
    msg = error_text("en", NoConverter("none"), jobs, lib)
    assert "mem/cvlt/rating.docx" in msg and "LibreOffice" in msg
    msg = error_text("en", OutputError(tmp_path / "out.pdf", "denied"), jobs, lib)
    assert str(tmp_path / "out.pdf") in msg and "denied" in msg
    assert "disk full" in error_text("en", OSError("disk full"), jobs, lib)


def test_error_text_output_says_what_was_written(tmp_path):
    out, done = tmp_path / "b.pdf", tmp_path / "a.pdf"
    msg = error_text("en", OutputError(out, "denied", [done]), {}, tmp_path)
    assert str(out) in msg and str(done) in msg and "Nothing was written" not in msg
    assert "Rien n'a été écrit" in error_text("fr", OutputError(out, "denied"), {}, tmp_path)


def test_build_jobs_same_file_differing_in_case(tmp_path):
    plan = {"sheets": [Path("t.pdf")], "crfs": [Path("r.pdf")]}
    chosen = {"sheets": tmp_path / "Out.pdf", "crfs": tmp_path / "out.PDF"}
    for platform in ("darwin", "win32"):
        with pytest.raises(ValueError):
            build_jobs(plan, chosen, platform)
    if sys.platform != "win32":  # Windows paths are never case-sensitive
        assert len(build_jobs(plan, chosen, "linux")) == 2


def test_in_library(tmp_path):
    lib = tmp_path / "Tests Lib"
    (lib / "Mem" / "TMT").mkdir(parents=True)
    assert in_library(lib / "Mem" / "TMT" / "test.pdf", lib)
    assert in_library(lib / "x.pdf", lib)
    assert in_library(tmp_path / "tests lib" / "Mem" / "x.pdf", lib, "darwin")  # case-insensitive
    assert in_library(tmp_path / "other" / ".." / "Tests Lib" / "x.pdf", lib)
    assert not in_library(tmp_path / "Tests Library" / "x.pdf", lib)  # a sibling, not inside
    assert not in_library(tmp_path / "out.pdf", lib)
    if sys.platform != "win32":  # Windows paths are never case-sensitive
        assert not in_library(tmp_path / "tests lib" / "x.pdf", lib, "linux")
