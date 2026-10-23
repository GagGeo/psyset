import sys

from psyset import platform as plat


def test_asset_path_found_and_missing(tmp_path, monkeypatch):
    (tmp_path / "assets" / "logo").mkdir(parents=True)
    (tmp_path / "assets" / "logo" / "x.png").write_bytes(b"")
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert plat.asset_path("logo", "x.png") == tmp_path / "assets" / "logo" / "x.png"
    assert plat.asset_path("logo", "missing.png") is None
