import json
import sys

import pytest

from psyset.library import (
    LibraryMissing,
    list_domains,
    parse_role,
    read_info,
    scan_library,
    write_info,
)


def one(root):
    (inst,) = scan_library(root)
    return inst


def test_roles_detected(make_lib):
    root = make_lib({"Exec": {"tmt": [
        "test.pdf", "rating.pdf", "instructions.pdf", "norms.pdf", "norm-calculation.xlsx"]}})
    t = one(root)
    folder = root / "Exec" / "tmt"
    assert t.sheets == {"": folder / "test.pdf"}
    assert t.crfs == {"": folder / "rating.pdf"}
    assert len(t.instructions) == 1
    assert len(t.norms) == 2
    assert t.unclassified == []


def test_role_detection_case_insensitive(make_lib):
    t = one(make_lib({"Exec": {"tmt": ["Test.PDF", "RATING.docx"]}}))
    assert list(t.sheets) == [""] and t.sheets[""].name == "Test.PDF"
    assert t.crfs[""].name == "RATING.docx"


def test_versions_labels(make_lib):
    t = one(make_lib({"Exec": {"tmt": [
        "test.pdf", "rating-B.pdf", "rating-A.pdf", "rating-10.pdf", "rating-2.pdf"]}}))
    assert t.sheets.keys() == {""}
    assert t.versions() == ["2", "10", "A", "B"]


def test_unclassified_and_ignored(make_lib):
    root = make_lib({"Exec": {"tmt": [
        "merged-inst.pdf", ".DS_Store", "~$rating.docx", "psyset.json"]}})
    (root / "Exec" / "tmt" / "sub").mkdir()
    t = one(root)
    assert [p.name for p in t.unclassified] == ["merged-inst.pdf"]
    assert t.sheets == t.crfs == {}
    assert t.instructions == t.norms == t.unsupported == []


def test_unsupported_sheet_format(make_lib):
    root = make_lib({"Exec": {"tmt": ["rating.xlsx"]}})
    t = one(root)
    assert t.crfs == {}
    assert t.unsupported == [root / "Exec" / "tmt" / "rating.xlsx"]


def test_duplicate_prefers_pdf(make_lib):
    root = make_lib({"Exec": {"tmt": ["test.docx", "test.pdf"]}})
    t = one(root)
    folder = root / "Exec" / "tmt"
    assert t.sheets[""] == folder / "test.pdf"
    assert t.duplicates == [folder / "test.docx"]


def test_info_file_used(make_lib):
    root = make_lib({"Exec": {"RL-RI-16": ["test.pdf"]}})
    info = {"name": "RL/RI-16", "reference": "Van der Linden 2004", "subdomain": "Episodic"}
    (root / "Exec" / "RL-RI-16" / "psyset.json").write_text(json.dumps(info), encoding="utf-8")
    t = one(root)
    assert t.name == "RL/RI-16" and t.has_info
    assert t.reference == "Van der Linden 2004" and t.subdomain == "Episodic"


def test_info_absent_or_invalid(make_lib):
    root = make_lib({"Exec": {"a": ["test.pdf"], "b": ["test.pdf", "psyset.json"]}})
    (root / "Exec" / "b" / "psyset.json").write_text("{not json", encoding="utf-8")
    a, b = scan_library(root)
    assert (a.name, a.has_info) == ("a", False)
    assert (b.name, b.has_info) == ("b", False)
    assert read_info(root / "Exec" / "b") is None


def test_domains_and_sort(make_lib):
    root = make_lib({
        "Mem": {"cvlt": ["test.pdf"]},
        "Exec": {"zeta": ["test.pdf"], "Alpha": ["test.pdf"], "beta": ["test.pdf"]},
    })
    (root / "stray.pdf").write_bytes(b"x")
    (root / "Exec" / "stray.pdf").write_bytes(b"x")
    write_info(root / "Exec" / "zeta", "zeta", "", "Inhibition")
    assert list_domains(root) == ["Exec", "Mem"]
    assert [(t.domain, t.name) for t in scan_library(root)] == [
        ("Exec", "zeta"), ("Exec", "Alpha"), ("Exec", "beta"), ("Mem", "cvlt")]


def test_scan_missing_root_raises(tmp_path):
    with pytest.raises(LibraryMissing):
        scan_library(tmp_path / "nope")


def test_key_is_posix_relative(make_lib):
    root = make_lib({"Exec": {"tmt": ["test.pdf"]}})
    assert one(root).key(root) == "Exec/tmt"


def test_write_info_roundtrip(make_lib):
    root = make_lib({"Exec": {"x": []}})
    folder = root / "Exec" / "x"
    write_info(folder, "Rappel é/ü", "Réf. 2004", "Épisodique")
    assert read_info(folder) == {"name": "Rappel é/ü", "reference": "Réf. 2004", "subdomain": "Épisodique"}
    assert "Rappel é/ü" in (folder / "psyset.json").read_text(encoding="utf-8")


def test_info_non_string_values_ignored(make_lib):
    root = make_lib({"Exec": {"a": ["test.pdf"], "b": ["test.pdf"]}})
    (root / "Exec" / "a" / "psyset.json").write_text(
        json.dumps({"name": 16, "reference": ["x"], "subdomain": 3}), encoding="utf-8")
    a, b = scan_library(root)
    assert (a.name, a.reference, a.subdomain, a.has_info) == ("a", "", "", True)


def test_info_with_bom(make_lib):
    root = make_lib({"Exec": {"a": ["test.pdf"]}})
    (root / "Exec" / "a" / "psyset.json").write_bytes(
        b"\xef\xbb\xbf" + json.dumps({"name": "Z", "subdomain": "S"}).encode())
    t = one(root)
    assert (t.name, t.subdomain, t.has_info) == ("Z", "S", True)


def test_natural_key_non_decimal_digits():
    from psyset.library import natural_key
    assert sorted(["10", "1²", "2"], key=natural_key) == ["1²", "2", "10"]  # "²" is no number


def test_system_files_ignored(make_lib):
    clutter = ["Thumbs.db", "DESKTOP.INI"] + ([] if sys.platform == "win32" else ["Icon\r"])
    t = one(make_lib({"Exec": {"tmt": ["test.pdf", *clutter]}}))
    assert t.unclassified == [] and list(t.sheets) == [""]


@pytest.fixture
def locked(request):
    """chmod 000 a folder; permissions are restored at teardown."""
    import os
    done = []

    def lock(path):
        os.chmod(path, 0)
        done.append(path)
    yield lock
    for p in reversed(done):  # a locked parent first would block its children
        os.chmod(p, 0o755)


@pytest.mark.skipif(sys.platform == "win32", reason="chmod cannot lock a folder on Windows")
def test_unreadable_folders_skipped(make_lib, locked):
    root = make_lib({"Exec": {"tmt": ["test.pdf"], "locked": ["test.pdf"]},
                     "Hidden drive dir": {"x": ["test.pdf"]}})
    locked(root / "Exec" / "locked")
    locked(root / "Hidden drive dir")
    assert [(i.domain, i.name) for i in scan_library(root)] == [("Exec", "tmt")]
    from psyset.ui.dialogs import library_problem
    assert library_problem({"library": str(root)}) is None
    locked(root)  # the root itself unreadable: still a library problem
    with pytest.raises(OSError):
        scan_library(root)


def test_parse_role_any_prefix_last_role_word_wins():
    assert parse_role("test") == ("test", "")
    assert parse_role("cvlt-test") == ("test", "")
    assert parse_role("CVLT_rating_A") == ("rating", "A")
    assert parse_role("TMT rating B") == ("rating", "B")
    assert parse_role("rating-scale-test") == ("test", "")  # the test's own name holds a role word
    assert parse_role("cvlt-instructions") == ("instructions", "")
    assert parse_role("norm-calculation") == ("norms", "")
    assert parse_role("cvlt-norms") == ("norms", "")
    assert parse_role("testament") is None and parse_role("merged-inst") is None


def test_prefixed_names_are_recognised(make_lib):
    t = one(make_lib({"Mem": {"cvlt": ["cvlt-test.pdf", "cvlt-rating-A.pdf", "CVLT_rating_B.docx",
                                       "cvlt-instructions.doc", "cvlt-norms.jpg"]}}))
    assert list(t.sheets) == [""] and sorted(t.crfs) == ["A", "B"] and t.versions() == ["A", "B"]
    assert len(t.instructions) == len(t.norms) == 1 and t.unclassified == []
