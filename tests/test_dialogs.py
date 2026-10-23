from pathlib import Path

import pytest

from .conftest import pdf
from psyset.i18n import t
from psyset.ui import dialogs
from psyset.ui.dialogs import (ParkedFiles, apply_plans, form_error, library_problem,
                               next_label, plan_files, role_labels, trash_word)


def names(folder):
    return {p.name for p in folder.iterdir()}


def test_next_label():
    assert next_label([]) == "A"
    assert next_label(["A"]) == "B"
    assert next_label(["a", " B "]) == "C"   # case-insensitive, stripped
    assert next_label(["B"]) == "A"          # first free letter
    assert next_label([chr(c) for c in range(65, 91)]) == "1"


def test_trash_word():
    assert trash_word("fr", "darwin") == "Corbeille"
    assert trash_word("fr", "win32") == "Corbeille"
    assert trash_word("en", "darwin") == "Trash"
    assert trash_word("en", "win32") == "Recycle Bin"
    assert trash_word("en", "linux") == "Trash"


def test_library_problem(tmp_path, monkeypatch):
    assert library_problem({}) == ""                       # never configured
    assert library_problem({"library": 3}) == ""
    assert library_problem({"library": str(tmp_path)}) is None
    gone = str(tmp_path / "gone")
    assert library_problem({"library": gone}) == gone      # LibraryMissing

    def offline(_root):
        raise PermissionError(13, "Permission denied", str(tmp_path))
    monkeypatch.setattr(dialogs, "scan_library", offline)
    assert library_problem({"library": str(tmp_path)}) == f"{tmp_path}\nPermission denied"


def test_form_error_name_and_domain():
    assert form_error("en", "  ", "Memory") == t("en", "err_name_empty")
    assert form_error("fr", "TMT", " ") == t("fr", "err_domain_empty")
    assert form_error("en", "...", "Memory") == t("en", "err_name_invalid")
    assert form_error("en", "RL/RI-16", "Memory") is None


F = Path("/lib/Memory/RL")


def old(name, label, typed=None):  # an existing file as the form lists it
    return {"path": F / name, "src": None, "current": label,
            "label": label if typed is None else typed}


def new(name, typed):  # a picked file
    return {"path": None, "src": Path("/picks") / name, "current": "", "label": typed}


def test_plan_add_mode_labels():
    plan = lambda *labels: plan_files("en", "rating", [new(f"{n}.pdf", lb) for n, lb in
                                                      enumerate(labels)], [])
    crfs = t("en", "f_crfs")
    assert plan("A") == ([("put", Path("/picks/0.pdf"), "", None)], None)  # lone file: no label
    assert plan("A", "B")[1] is None
    assert plan("A", " ") == ([], t("en", "err_label_empty", role=crfs))
    assert plan("A", "a") == ([], t("en", "err_label_dup", label="A", role=crfs))
    assert plan("A/B", "A-B") == ([], t("en", "err_label_dup", label="A/B", role=crfs))
    assert plan("A", "...") == ([], t("en", "err_label_invalid", label="..."))


def test_plan_save_touching_no_file_renames_nothing():
    # mixed state: a shared test.pdf next to test-A.pdf; the user only edits the reference
    rows = [old("test.pdf", ""), old("test-A.pdf", "A")]
    assert plan_files("en", "test", rows, []) == ([], None)
    rows = [old("rating.pdf", ""), old("rating-A.pdf", "A"), old("rating-B.pdf", "B")]
    assert plan_files("en", "rating", rows, [F / "rating-A.docx"]) == ([], None)  # duplicate untouched


def test_plan_version_added_to_lone_file():
    rows = [old("test.pdf", "", typed="A"), new("v2.pdf", "B")]
    assert plan_files("en", "test", rows, []) == (
        [("rename", F / "test.pdf", "A"), ("put", Path("/picks/v2.pdf"), "B", None)], None)


def test_plan_swaps_and_replacements_are_planned_not_refused():
    swap = [old("rating-A.pdf", "A", typed="B"), old("rating-B.pdf", "B", typed="A")]
    assert plan_files("en", "rating", swap, []) == (
        [("rename", F / "rating-A.pdf", "B"), ("rename", F / "rating-B.pdf", "A")], None)
    a_replaced = dict(old("rating-A.pdf", "A", typed="C"), src=Path("/picks/new.pdf"))
    rows = [a_replaced, old("rating-B.pdf", "B", typed="A")]
    assert plan_files("en", "rating", rows, []) == (
        [("put", Path("/picks/new.pdf"), "C", F / "rating-A.pdf"),
         ("rename", F / "rating-B.pdf", "A")], None)


def test_plan_refuses_to_replace_a_file_the_form_does_not_show():
    rows = [old("rating-A.pdf", "A"), old("rating-B.pdf", "B"), new("c.pdf", "C")]
    assert plan_files("en", "rating", rows, [F / "rating-C.xlsx"]) == (
        [], t("en", "err_hidden_file", file="rating-C.xlsx"))
    # a lone new sheet would be test.pdf and replace an unsupported test.xlsx
    assert plan_files("en", "test", [new("s.pdf", "A")], [F / "test.xlsx"]) == (
        [], t("en", "err_hidden_file", file="test.xlsx"))
    # relabelling onto a hidden duplicate's label is refused too
    rows = [old("rating-A.pdf", "A", typed="B"), old("rating-C.pdf", "C")]
    assert plan_files("en", "rating", rows, [F / "rating-B.docx"])[1] == \
        t("en", "err_hidden_file", file="rating-B.docx")
    # norms never replace anything
    assert plan_files("en", "norms", [new("n.pdf", "")], [F / "norms.pdf"])[1] is None


def test_role_labels():
    files = [F / "rating-C.xlsx", F / "test.xlsx", F / "rating.odt", F / "notes.txt"]
    assert role_labels(files, "rating") == ["C", ""]
    assert role_labels(files, "test") == [""]


def test_form_plural_strings():
    assert t("fr", "f_sheets") == "Feuilles patient"
    assert t("en", "f_sheets") == "Patient sheets"
    assert t("fr", "f_crfs") == "CRF"
    assert t("en", "f_crfs") == "CRFs"


def test_confirm_uses_trash_word():
    assert t("en", "confirm_remove_test", name="TMT", trash="Recycle Bin") == \
        "Move “TMT” to the Recycle Bin?"
    assert t("fr", "confirm_remove_test", name="TMT", trash="Corbeille") == \
        "Mettre « TMT » à la Corbeille ?"


def test_plan_label_with_stray_space_is_unchanged():
    # test-A .pdf on disk: label "A " is shown stripped; saving untouched renames nothing
    rows = [old("test-A .pdf", "A ", typed="A"), old("test-B.pdf", "B")]
    assert plan_files("en", "test", rows, []) == ([], None)


def test_plan_instructions_replacement_must_not_overwrite_the_other_listed_file():
    docx = dict(old("instructions.docx", ""), src=Path("/picks/new.pdf"))
    rows = [docx, old("instructions.pdf", "")]
    assert plan_files("en", "instructions", rows, []) == (
        [], t("en", "err_file_exists", file="instructions.pdf"))
    pdf_row = dict(old("instructions.pdf", ""), src=Path("/picks/new.PDF"))
    assert plan_files("en", "instructions", [old("instructions.docx", ""), pdf_row], []) == (
        [("put", Path("/picks/new.PDF"), "", F / "instructions.pdf")], None)


@pytest.fixture
def trash(monkeypatch):
    sent = []
    def to_trash(p):  # like the real Trash: the file is gone afterwards
        sent.append(p)
        Path(p).unlink()
    monkeypatch.setattr(dialogs.manage.send2trash, "send2trash", to_trash)
    return sent


def test_apply_plans_swap_and_instructions_replace(make_lib, tmp_path, trash):
    root = make_lib({"A": {"T": ["rating-A.pdf", "rating-B.docx", "instructions.docx",
                                 "instructions.pdf"]}})
    folder = root / "A" / "T"
    (folder / "rating-A.pdf").write_bytes(b"was A")
    plans = {"rating": [("rename", folder / "rating-A.pdf", "B"),
                        ("rename", folder / "rating-B.docx", "A")],
             "instructions": [("put", pdf(tmp_path / "i.pdf"), "", folder / "instructions.pdf")]}
    apply_plans(folder, plans)
    assert (folder / "t-rating-B.pdf").read_bytes() == b"was A" and (folder / "t-rating-A.docx").exists()
    assert trash == [str(folder / "instructions.pdf")]  # the .docx is kept
    assert (folder / "instructions.docx").exists() and (folder / "t-instructions.pdf").exists()


def test_apply_plans_failure_restores_parked_files(make_lib, tmp_path, trash, monkeypatch):
    root = make_lib({"A": {"T": ["rating-A.pdf", "rating-B.pdf"]}})
    folder = root / "A" / "T"
    before = names(folder)

    def broken(*_a, **_k):
        raise OSError("disk full")
    monkeypatch.setattr(dialogs.manage, "put_file", broken)
    plans = {"rating": [("rename", folder / "rating-A.pdf", "C"),
                        ("put", pdf(tmp_path / "n.pdf"), "D", None)]}
    with pytest.raises(OSError):
        apply_plans(folder, plans)
    assert names(folder) == before  # parked file got its name back


def test_apply_plans_reports_a_file_it_could_not_restore(make_lib, tmp_path, monkeypatch):
    root = make_lib({"A": {"T": ["rating-A.pdf"]}})
    folder = root / "A" / "T"
    real = dialogs.os.rename

    def park_only(src, dst):
        if not Path(dst).name.startswith("psyset-parked-"):
            raise PermissionError(13, "in use")
        real(src, dst)
    monkeypatch.setattr(dialogs.os, "rename", park_only)
    monkeypatch.setattr(dialogs.manage, "assign_role", lambda *a: (_ for _ in ()).throw(OSError()))
    with pytest.raises(ParkedFiles) as e:
        apply_plans(folder, {"rating": [("rename", folder / "rating-A.pdf", "B")]})
    (left,) = names(folder)
    assert e.value.names == [left] and left.startswith("psyset-parked-")
    assert left.endswith("-rating-A.pdf")  # visible, and says what it was
