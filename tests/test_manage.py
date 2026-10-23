from pathlib import Path

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
    assert manage.sanitize_folder_name(".hidden") == "hidden"
    assert manage.sanitize_folder_name("..x") == "x"
    for bad in ("   ", "..", ".", ""):
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


def test_add_test_nfd_existing_folder_is_a_collision_and_untouched(make_lib, tmp_path):
    import unicodedata
    nfd, nfc = (unicodedata.normalize(f, "\u00c9preuve") for f in ("NFD", "NFC"))
    root = make_lib({"Att": {nfd: ["test.pdf"]}})
    with pytest.raises(AlreadyExists):
        manage.add_test(root, "Att", nfc, "", "", [("", pdf(tmp_path / "s.pdf"))], [], None, [])
    assert [p.name for p in (root / "Att").iterdir()] == [nfd]
    assert (root / "Att" / nfd / "test.pdf").exists()


def test_add_test_failure_never_removes_preexisting_folder(make_lib, tmp_path, monkeypatch):
    root = make_lib({"Att": {"T": ["test.pdf"]}})
    monkeypatch.setattr(manage, "_find_entry", lambda *a, **k: None)  # simulate an undetected clash
    with pytest.raises(FileExistsError):
        manage.add_test(root, "Att", "T", "", "", [("", pdf(tmp_path / "s.pdf"))], [], None, [])
    assert (root / "Att" / "T" / "test.pdf").exists()


def test_update_info_keeps_folder_name_when_display_name_unchanged(make_lib):
    root = make_lib({"Att": {"hand-renamed": ["test.pdf"]}})
    folder = root / "Att" / "hand-renamed"
    manage.write_info(folder, "RL/RI 16: long", "", "")
    new = manage.update_info(folder, root, "RL/RI 16: long", "new ref", "", "Att")
    assert new == folder and read_info(new)["reference"] == "new ref"
    # no psyset.json: display name defaults to the folder name
    bare = make_lib({"Att": {"Bare": ["test.pdf"]}})
    assert manage.update_info(bare / "Att" / "Bare", bare, "Bare", "r", "", "Att") == bare / "Att" / "Bare"
    moved = manage.update_info(folder, root, "RL/RI 16: long", "x", "", "Memoire")
    assert moved == root / "Memoire" / "hand-renamed"


def _snapshot(root):
    return sorted((p.relative_to(root).as_posix(), p.read_bytes() if p.is_file() else None)
                  for p in root.rglob("*"))


def test_update_info_move_failure_copies_and_deletes_nothing(make_lib, monkeypatch):
    root = make_lib({"Mem": {"TMT": ["test.pdf"]}})
    folder = root / "Mem" / "TMT"
    manage.write_info(folder, "TMT", "r", "")
    before = _snapshot(root)

    def busy(*_a):
        raise PermissionError(13, "file in use")
    monkeypatch.setattr(manage.os, "rename", busy)
    monkeypatch.setattr(manage.shutil, "copytree", lambda *a, **k: pytest.fail("copied"))
    monkeypatch.setattr(manage.shutil, "rmtree", lambda *a, **k: pytest.fail("deleted"))
    for name, domain in (("TMT-2", "Mem"), ("TMT", "New domain"), ("tmt", "Mem")):
        with pytest.raises(manage.FolderBusy) as e:
            manage.update_info(folder, root, name, "changed", "", domain)
        assert e.value.path == folder
        assert _snapshot(root) == before  # folder intact, psyset.json unchanged, no new domain


def test_case_only_rename_second_step_fails_rolls_back(make_lib, monkeypatch):
    root = make_lib({"Att": {"TMT": ["test.pdf"]}})
    folder = root / "Att" / "TMT"
    real, calls = manage.os.rename, []

    def second_fails(src, dst):
        calls.append(Path(dst).name)
        if len(calls) == 2:
            raise PermissionError(13, "file in use")
        real(src, dst)
    monkeypatch.setattr(manage.os, "rename", second_fails)
    with pytest.raises(manage.FolderBusy) as e:
        manage.update_info(folder, root, "tmt", "", "", "Att")
    assert calls[0].startswith("psyset-renaming-") and calls[0].endswith("-TMT")  # visible
    assert names(root / "Att") == {"TMT"} and e.value.path == folder  # rolled back


def test_case_only_rename_rollback_fails_leaves_it_visible(make_lib, monkeypatch):
    root = make_lib({"Att": {"TMT": ["test.pdf"]}})
    real, calls = manage.os.rename, []

    def only_first_works(src, dst):
        calls.append(dst)
        if len(calls) > 1:
            raise PermissionError(13, "file in use")
        real(src, dst)
    monkeypatch.setattr(manage.os, "rename", only_first_works)
    with pytest.raises(manage.FolderBusy) as e:
        manage.update_info(root / "Att" / "TMT", root, "tmt", "", "", "Att")
    (left,) = (root / "Att").iterdir()
    assert not left.name.startswith(".") and e.value.path == left
    assert (left / "test.pdf").exists()


def test_put_instructions_replaces_only_the_named_file(make_lib, tmp_path, trash):
    root = make_lib({"A": {"T": ["instructions.docx", "instructions.pdf"]}})
    folder = root / "A" / "T"
    # replacing the .pdf by a .pdf: only that file goes to the Trash
    dest = manage.put_file(folder, "instructions", pdf(tmp_path / "new.pdf"),
                           replaces=folder / "instructions.pdf")
    assert dest == folder / "instructions.pdf" and trash == [str(folder / "instructions.pdf")]
    assert (folder / "instructions.docx").exists()
    # replacing the .docx by a PDF would overwrite the other listed file: refused
    with pytest.raises(AlreadyExists):
        manage.put_file(folder, "instructions", pdf(tmp_path / "n2.pdf"),
                        replaces=folder / "instructions.docx")
    assert len(trash) == 1 and names(folder) == {"instructions.docx", "instructions.pdf"}
    with pytest.raises(AlreadyExists):  # nothing named to replace: an existing file is kept
        manage.put_file(folder, "instructions", pdf(tmp_path / "n3.pdf"))
    assert len(trash) == 1
