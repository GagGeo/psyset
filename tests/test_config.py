import json
import os
import sys

from psyset import config


def test_config_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "config_path", lambda: tmp_path / "sub" / "config.json")
    cfg = {"lang": "fr", "library": "/x/Tests é", "duplex": True, "outputs": {"sheets": True}}
    config.save_config(cfg)
    assert config.load_config() == cfg


def test_config_missing_returns_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "config_path", lambda: tmp_path / "nope.json")
    assert config.load_config() == {}


def test_config_invalid_json_returns_empty(tmp_path, monkeypatch):
    p = tmp_path / "config.json"
    monkeypatch.setattr(config, "config_path", lambda: p)
    p.write_text("{not json", encoding="utf-8")
    assert config.load_config() == {}
    p.write_text(json.dumps(["not", "a", "dict"]), encoding="utf-8")
    assert config.load_config() == {}


def test_save_config_never_raises(tmp_path, monkeypatch):
    blocker = tmp_path / "file"
    blocker.write_text("x")  # a file where a directory is needed -> OSError
    monkeypatch.setattr(config, "config_path", lambda: blocker / "config.json")
    config.save_config({"lang": "en"})  # must not raise


def test_config_path_per_platform(monkeypatch):
    # _config_dir returns str on purpose: pathlib refuses to build a WindowsPath on posix.
    monkeypatch.setattr(sys, "platform", "darwin")
    assert config._config_dir().replace("\\", "/").endswith("Library/Application Support/PsySet")
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(os, "name", "nt")
    monkeypatch.setenv("APPDATA", "C:/Users/me/AppData/Roaming")
    assert config._config_dir() == os.path.join("C:/Users/me/AppData/Roaming", "PsySet")
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(os, "name", "posix")
    assert config._config_dir().replace("\\", "/").endswith(".config/PsySet")


def test_save_config_non_serialisable_never_raises(tmp_path, monkeypatch):
    p = tmp_path / "config.json"
    monkeypatch.setattr(config, "config_path", lambda: p)
    config.save_config({"lang": "fr"})
    config.save_config({"library": tmp_path})  # a Path: TypeError inside json.dumps
    loop = {}
    loop["self"] = loop
    config.save_config(loop)  # circular reference: ValueError inside json.dumps
    assert config.load_config() == {"lang": "fr"}  # old file intact


def test_save_config_keeps_old_file_on_write_failure(tmp_path, monkeypatch):
    p = tmp_path / "config.json"
    monkeypatch.setattr(config, "config_path", lambda: p)
    config.save_config({"lang": "fr"})

    def boom(src, dst):
        raise OSError("disk full")
    monkeypatch.setattr(config.os, "replace", boom)
    config.save_config({"lang": "en"})
    assert config.load_config() == {"lang": "fr"}
    assert [f.name for f in tmp_path.iterdir()] == ["config.json"]  # no temp file left
