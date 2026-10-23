from psyset.i18n import t
from psyset.ui import dialogs
from psyset.ui.dialogs import form_error, library_problem, next_label, trash_word


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
    assert form_error("en", "  ", "Memory", {}) == t("en", "err_name_empty")
    assert form_error("fr", "TMT", " ", {}) == t("fr", "err_domain_empty")
    assert form_error("en", "...", "Memory", {}) == t("en", "err_name_invalid")
    assert form_error("en", "RL/RI-16", "Memory", {}) is None


def test_form_error_labels():
    ok = lambda labels: form_error("en", "TMT", "Memory", {"f_crfs": labels})
    assert ok([""]) is None                    # a single file needs no label
    assert ok(["A", "B"]) is None
    assert ok(["A", " "]) == t("en", "err_label_empty", role=t("en", "f_crfs"))
    assert ok(["A", "a"]) == t("en", "err_label_dup", label="a", role=t("en", "f_crfs"))
    assert ok(["A/B", "A-B"]) == t("en", "err_label_dup", label="A-B", role=t("en", "f_crfs"))
    assert ok(["A", "..."]) == t("en", "err_label_invalid", label="...")


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
