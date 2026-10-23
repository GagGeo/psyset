import pytest
from pypdf import PdfReader, PdfWriter

from psyset.pdf import PdfReadError, estimate, merge, page_count
from tests.conftest import pdf


def widths(path):
    return [float(p.mediabox.width) for p in PdfReader(path).pages]


def three(tmp_path):
    return [pdf(tmp_path / "a.pdf", 1, width=100),
            pdf(tmp_path / "b.pdf", 3, width=200),
            pdf(tmp_path / "c.pdf", 2, width=300)]


def test_merge_order_and_count(tmp_path):
    out = tmp_path / "out.pdf"
    assert merge(three(tmp_path), out, duplex=False) == 6
    assert widths(out) == [100, 200, 200, 200, 300, 300]


def test_merge_duplex_pads_odd_docs(tmp_path):
    out = tmp_path / "out.pdf"
    assert merge(three(tmp_path), out, duplex=True) == 8
    w = widths(out)
    assert w == [100, 100, 200, 200, 200, 200, 300, 300]
    pages = PdfReader(out).pages
    for i in (1, 5):  # the blanks (pages 2 and 6)
        assert not pages[i].get("/Contents")  # blank
        assert pages[i].mediabox == pages[i - 1].mediabox


def test_merge_duplex_last_doc_odd_is_padded(tmp_path):
    out = tmp_path / "out.pdf"
    assert merge([pdf(tmp_path / "a.pdf", 1)], out, duplex=True) == 2
    assert len(PdfReader(out).pages) == 2


def test_estimate(tmp_path):
    docs = [pdf(tmp_path / "1p.pdf", 1), pdf(tmp_path / "3p.pdf", 3), tmp_path / "x.docx"]
    assert estimate(docs, duplex=True) == (6, 1)
    assert estimate(docs, duplex=False) == (4, 1)
    assert estimate([pdf(tmp_path / "U.PDF", 1)], duplex=False) == (1, 0)


def test_estimate_corrupt_pdf_raises(tmp_path):
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"nope")
    with pytest.raises(PdfReadError) as e:
        estimate([bad], duplex=False)
    assert e.value.path == bad


def test_page_count_cached_by_mtime(tmp_path):
    p = pdf(tmp_path / "a.pdf", 2)
    assert page_count(p) == 2
    pdf(p, 5)
    import os
    st = p.stat()
    os.utime(p, ns=(st.st_atime_ns, st.st_mtime_ns + 10**9))  # guarantee a new mtime
    assert page_count(p) == 5


def test_merge_owner_password_pdf(tmp_path):
    src = pdf(tmp_path / "plain.pdf", 2, width=123)
    w = PdfWriter(clone_from=src)
    w.encrypt(user_password="", owner_password="owner")
    enc = tmp_path / "enc.pdf"
    with enc.open("wb") as f:
        w.write(f)
    out = tmp_path / "out.pdf"
    assert merge([enc], out, duplex=False) == 2
    assert widths(out) == [123, 123]


def test_merge_owner_password_aes_pdf(tmp_path):
    src = pdf(tmp_path / "plain.pdf", 2, width=123)
    w = PdfWriter(clone_from=src)
    w.encrypt(user_password="", owner_password="owner", algorithm="AES-256")
    enc = tmp_path / "enc.pdf"
    with enc.open("wb") as f:
        w.write(f)
    out = tmp_path / "out.pdf"
    assert merge([enc], out, duplex=False) == 2
    assert widths(out) == [123, 123]


def test_merge_corrupt_pdf_names_file(tmp_path):
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"garbage bytes, not a pdf")
    out = tmp_path / "out.pdf"
    with pytest.raises(PdfReadError) as e:
        merge([pdf(tmp_path / "ok.pdf"), bad], out, duplex=False)
    assert e.value.path == bad
    assert "bad.pdf" in str(e.value)
    assert not out.exists()


def test_merge_overwrites_atomically(tmp_path):
    out = tmp_path / "out.pdf"
    out.write_bytes(b"old")
    ok = pdf(tmp_path / "ok.pdf", 2)
    assert merge([ok], out, duplex=False) == 2
    assert len(PdfReader(out).pages) == 2

    out.write_bytes(b"old")
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"garbage")
    with pytest.raises(PdfReadError):
        merge([ok, bad], out, duplex=False)
    assert out.read_bytes() == b"old"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["bad.pdf", "ok.pdf", "out.pdf"]
