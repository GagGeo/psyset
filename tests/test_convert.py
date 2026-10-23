import shutil
import subprocess

import pytest

from psyset import convert
from psyset.convert import ConversionError, NoConverter, OutputError, generate, to_pdf
from psyset.pdf import PdfReadError, page_count

from .conftest import pdf


def make_fake(tmp_path, fail_on=None):
    two_pages = pdf(tmp_path / "two.pdf", pages=2)
    calls = []

    def fake(src, out_dir):
        calls.append(src)
        if src.name == fail_on:
            raise ConversionError(src, "boom")
        return shutil.copy(two_pages, out_dir / f"{src.stem}.pdf")

    return fake, calls


def test_generate_converts_once_and_merges(tmp_path):
    fake, calls = make_fake(tmp_path)
    x = tmp_path / "x.docx"
    x.write_bytes(b"w")
    one = pdf(tmp_path / "one.pdf")
    a, b = tmp_path / "a.pdf", tmp_path / "b.pdf"
    result = generate({a: [one, x], b: [x]}, duplex=False, convert=fake)
    assert calls == [x]
    assert result == {a: 3, b: 2}
    assert page_count(a) == 3 and page_count(b) == 2
    assert sorted(p.name for p in tmp_path.iterdir() if p.suffix == ".pdf") == ["a.pdf", "b.pdf", "one.pdf", "two.pdf"]


def test_generate_failure_writes_nothing(tmp_path):
    fake, _ = make_fake(tmp_path, fail_on="y.docx")
    x, y = tmp_path / "x.docx", tmp_path / "y.docx"
    a, b = tmp_path / "a.pdf", tmp_path / "b.pdf"
    with pytest.raises(ConversionError) as e:
        generate({a: [x], b: [y]}, duplex=False, convert=fake)
    assert e.value.path == y
    assert not a.exists() and not b.exists()


def test_generate_pdf_error_writes_nothing(tmp_path):
    good = pdf(tmp_path / "good.pdf")
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"not a pdf")
    a, b = tmp_path / "a.pdf", tmp_path / "b.pdf"
    with pytest.raises(PdfReadError) as e:
        generate({a: [good], b: [good, bad]}, duplex=False)
    assert e.value.path == bad
    assert not a.exists() and not b.exists()
    assert sorted(p.name for p in tmp_path.iterdir()) == ["bad.pdf", "good.pdf"]  # no stray temp files


def test_generate_destination_unwritable_names_it(tmp_path):
    good = pdf(tmp_path / "good.pdf")
    a = tmp_path / "a.pdf"
    b = tmp_path / "missing-folder" / "b.pdf"
    with pytest.raises(OutputError) as e:
        generate({a: [good], b: [good]}, duplex=False)
    assert e.value.path == b
    assert not a.exists()
    assert sorted(p.name for p in tmp_path.iterdir()) == ["good.pdf"]


def test_generate_destination_is_directory_names_it(tmp_path):
    good = pdf(tmp_path / "good.pdf")
    b = tmp_path / "b.pdf"
    b.mkdir()
    with pytest.raises(OutputError) as e:
        generate({b: [good]}, duplex=False)
    assert e.value.path == b
    assert sorted(p.name for p in tmp_path.iterdir()) == ["b.pdf", "good.pdf"]


def test_convert_timeout_raises(tmp_path, monkeypatch):
    def hang(*a, **k):
        raise subprocess.TimeoutExpired("soffice", convert.TIMEOUT)

    monkeypatch.setattr(subprocess, "run", hang)
    monkeypatch.setattr(convert, "find_converters", lambda: ["libreoffice"])
    src = tmp_path / "s.docx"
    src.write_bytes(b"w")
    with pytest.raises(ConversionError) as e:
        to_pdf(src, tmp_path)
    assert e.value.path == src
    assert "timed out" in e.value.reason


def test_converter_falls_back_to_next(tmp_path, monkeypatch):
    src = tmp_path / "s.docx"
    src.write_bytes(b"w")

    def word_fails(s, d):
        raise subprocess.CalledProcessError(1, "osascript", stderr="Word refused")

    monkeypatch.setitem(convert._CONVERTERS, "word", word_fails)
    monkeypatch.setitem(convert._CONVERTERS, "libreoffice", lambda s, d: pdf(d / "s.pdf"))
    assert to_pdf(src, tmp_path, ["word", "libreoffice"]) == tmp_path / "s.pdf"


def test_missing_output_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: None)
    src = tmp_path / "s.docx"
    src.write_bytes(b"w")
    with pytest.raises(ConversionError):
        to_pdf(src, tmp_path, ["libreoffice"])


def test_no_converter(tmp_path, monkeypatch):
    monkeypatch.setattr(convert, "find_converters", lambda: [])
    x = tmp_path / "x.docx"
    x.write_bytes(b"w")
    with pytest.raises(NoConverter):
        generate({tmp_path / "a.pdf": [x]}, duplex=False)
    assert not (tmp_path / "a.pdf").exists()
