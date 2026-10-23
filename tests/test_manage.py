import pytest

from .conftest import pdf
from psyset import manage
from psyset.library import read_info
from psyset.manage import AlreadyExists, InvalidName


@pytest.fixture
def trash(monkeypatch):
    sent = []
    monkeypatch.setattr(manage.send2trash, "send2trash", lambda p: sent.append(p))
    return sent


def names(folder):
    return {p.name for p in folder.iterdir()}


def test_sanitize_windows_chars():
    assert manage.sanitize_folder_name("RL/RI-16") == "RL-RI-16"
    assert manage.sanitize_folder_name('a<b>:c"d|e?f*') == "a-b--c-d-e-f-"
    assert manage.sanitize_folder_name("CON") == "CON_"
    assert manage.sanitize_folder_name("lpt1.txt") == "lpt1.txt_"
    assert manage.sanitize_folder_name("name. ") == "name"
    assert manage.sanitize_folder_name("a\tb") == "a-b"
    for bad in ("   ", "..", ""):
        with pytest.raises(InvalidName):
            manage.sanitize_folder_name(bad)


def _sources(tmp_path):
    src = tmp_path / "src"
    return dict(
        sheets=[("", pdf(src / "My Sheet.PDF"))],
        crfs=[("A", pdf(src / "crf1.pdf")), ("B", src / "crf2.docx")],
        instructions=pdf(src / "inst.pdf"),
        norms=[pdf(src / "n1.pdf"), src / "n2.JPG"],
    )


def test_add_test_layout(make_lib, tmp_path):
    root = make_lib({"Attention": {}})
    kw = _sources(tmp_path)
    kw["crfs"][1][1].write_bytes(b"docx")
    kw["norms"][1].write_bytes(b"jpg")
    before = {p: p.read_bytes() for p in (tmp_path / "src").iterdir()}
    folder = manage.add_test(root, "Attention", "TMT", "Ref", "Sub", **kw)
    assert folder == root / "Attention" / "TMT"
    assert names(folder) == {"test.pdf", "rating-A.pdf", "rating-B.docx", "instructions.pdf",
                             "norms.pdf", "norms-2.jpg", "psyset.json"}
    assert {p: p.read_bytes() for p in (tmp_path / "src").iterdir()} == before
    assert read_info(folder) == {"name": "TMT", "reference": "Ref", "subdomain": "Sub"}


def test_add_test_labels_rules(make_lib, tmp_path):
    root = make_lib({"Attention": {}})
    a, b = pdf(tmp_path / "a.pdf"), pdf(tmp_path / "b.pdf")
    for sheets in ([("", a), ("x", b)], [("X", a), ("x", b)]):
        with pytest.raises(InvalidName):
            manage.add_test(root, "Attention", "T", "", "", sheets, [], None, [])
    assert not (root / "Attention" / "T").exists()
    f = manage.add_test(root, "Attention", "T", "", "", [("ignored", a)], [], None, [])
    assert "test.pdf" in names(f)


def test_add_test_new_domain_created(make_lib, tmp_path):
    root = make_lib({})
    f = manage.add_test(root, "Nouveau/Domaine", "RL/RI-16", "", "",
                        [("", pdf(tmp_path / "s.pdf"))], [], None, [])
    assert f == root / "Nouveau-Domaine" / "RL-RI-16"
    assert read_info(f)["name"] == "RL/RI-16"


def test_add_test_collision_case_insensitive(make_lib, tmp_path):
    root = make_lib({"Attention": {"TMT": ["test.pdf"]}})
    with pytest.raises(AlreadyExists):
        manage.add_test(root, "Attention", "tmt", "", "", [("", pdf(tmp_path / "s.pdf"))], [], None, [])
    assert names(root / "Attention") == {"TMT"}


def test_add_test_cleanup_on_failure(make_lib, tmp_path):
    root = make_lib({})
    (root / "Attention").mkdir()
    with pytest.raises(OSError):
        manage.add_test(root, "Attention", "T", "", "", [("", pdf(tmp_path / "s.pdf"))],
                        [], tmp_path / "missing.pdf", [])
    assert names(root / "Attention") == set()
    with pytest.raises(OSError):  # a domain created for the failed add is removed too
        manage.add_test(root, "New", "T", "", "", [("", tmp_path / "missing.pdf")], [], None, [])
    assert names(root) == {"Attention"}


def test_update_info_rename_and_move(make_lib):
    root = make_lib({"Memoire": {"TMT": ["test.pdf", "psyset.json"]}, "Attention": {"TMT-B": ["x.pdf"]}})
    folder = root / "Memoire" / "TMT"
    with pytest.raises(AlreadyExists):
        manage.update_info(folder, root, "tmt-b", "r", "", "Attention")
    assert folder.exists()
    new = manage.update_info(folder, root, "TMT-C", "r", "s", "Attention")
    assert new == root / "Attention" / "TMT-C" and not folder.exists()
    assert (new / "test.pdf").exists()
    assert read_info(new) == {"name": "TMT-C", "reference": "r", "subdomain": "s"}


def test_update_info_case_only_rename_in_place(make_lib):
    root = make_lib({"Attention": {"TMT": ["test.pdf"]}})
    new = manage.update_info(root / "Attention" / "TMT", root, "tmt", "", "", "attention")
    assert [p.name for p in (root / "Attention").iterdir()] == ["tmt"]
    assert (new / "test.pdf").exists() and new.name == "tmt"


def test_put_file_replaces_same_role_label(make_lib, tmp_path, trash):
    root = make_lib({"A": {"T": ["rating-A.docx", "rating-B.docx"]}})
    folder = root / "A" / "T"
    dest = manage.put_file(folder, "rating", pdf(tmp_path / "new.PDF"), "A")
    assert dest == folder / "rating-A.pdf" and dest.exists()
    assert trash == [str(folder / "rating-A.docx")]
    assert not [p for p in folder.iterdir() if p.name.startswith(".")]


def test_put_file_norms_appends(make_lib, tmp_path, trash):
    root = make_lib({"A": {"T": ["norms.pdf"]}})
    folder = root / "A" / "T"
    assert manage.put_file(folder, "norms", pdf(tmp_path / "n.pdf")).name == "norms-2.pdf"
    assert manage.put_file(folder, "norms", pdf(tmp_path / "n.pdf")).name == "norms-3.pdf"
    assert trash == []


def test_put_file_failed_copy_keeps_old(make_lib, tmp_path, trash):
    root = make_lib({"A": {"T": ["test.pdf"]}})
    with pytest.raises(OSError):
        manage.put_file(root / "A" / "T", "test", tmp_path / "missing.pdf")
    assert trash == [] and (root / "A" / "T" / "test.pdf").exists()


def test_assign_role(make_lib):
    root = make_lib({"A": {"T": ["merged-inst-test.pdf", "other.PDF", "instructions.docx"]}})
    folder = root / "A" / "T"
    assert manage.assign_role(folder / "merged-inst-test.pdf", "instructions").name == "instructions.pdf"
    assert names(folder) == {"instructions.pdf", "other.PDF", "instructions.docx"}
    with pytest.raises(AlreadyExists):
        manage.assign_role(folder / "other.PDF", "instructions")
    assert manage.assign_role(folder / "other.PDF", "test", "V1").name == "test-V1.pdf"


def test_remove_uses_trash(make_lib, trash):
    root = make_lib({"A": {"T": ["test.pdf"]}})
    manage.remove_file(root / "A" / "T" / "test.pdf")
    manage.remove_test(root / "A" / "T")
    assert trash == [str(root / "A" / "T" / "test.pdf"), str(root / "A" / "T")]


def test_starter_library_fr(tmp_path):
    root = tmp_path / "new" / "lib"
    manage.create_starter_library(root, "fr")
    assert len(list(root.iterdir())) == 7 and (root / "Mémoire").is_dir()
    (root / "Mémoire" / "keep.txt").write_text("x")
    manage.create_starter_library(root, "fr")
    assert (root / "Mémoire" / "keep.txt").read_text() == "x"
