from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

import pytest

from backend import engine


@pytest.fixture(autouse=True)
def _isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(engine, "state_dir", lambda: tmp_path / "state")
    (tmp_path / "state").mkdir()
    for var in ("GODOT_PATH", "GODOT"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(engine.shutil, "which", lambda name: None)
    monkeypatch.setenv("ProgramFiles", str(tmp_path / "pf"))
    monkeypatch.setenv("ProgramFiles(x86)", str(tmp_path / "pf86"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    monkeypatch.setattr(engine.Path, "home", classmethod(lambda cls: tmp_path / "home"))


def test_parse_version():
    v = engine.parse_version("Godot Engine\n4.7.2.stable.official.ed1daf0bf\n")
    assert v == {"major": 4, "minor": 7, "patch": 2, "status": "stable", "text": "4.7.2.stable.official.ed1daf0bf"}
    assert engine.parse_version("4.8.beta1.official.abc")["status"] == "beta1"
    assert engine.parse_version("4.3.stable.official")["patch"] == 0
    assert engine.parse_version("garbage") is None


def _exe(folder: Path, name: str) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    path.write_bytes(b"")
    return path


def test_finds_steam_build_and_prefers_console(tmp_path, monkeypatch):
    steam = tmp_path / "pf86" / "Steam" / "steamapps" / "common" / "Godot Engine"
    _exe(steam, "Godot_v4.7.2-stable_win64.exe")
    console = _exe(steam, "Godot_v4.7.2-stable_win64_console.exe")
    monkeypatch.setattr(engine, "engine_version", lambda exe, timeout=20.0: engine.parse_version("4.7.2.stable.x"))
    found = engine.find_godot()
    assert found["ok"]
    assert Path(found["exe"]) == console
    assert Path(found["editor_exe"]).name == "Godot_v4.7.2-stable_win64.exe"


def test_godot3_is_skipped_and_explicit_path_is_remembered(tmp_path, monkeypatch):
    old = _exe(tmp_path / "pf" / "Godot3", "Godot_v3.6-stable_win64.exe")
    new = _exe(tmp_path / "tools", "Godot_v4.7.2-stable_win64.exe")
    versions = {str(old): "3.6.stable.x", str(new): "4.7.2.stable.x"}
    monkeypatch.setattr(engine, "engine_version", lambda exe, timeout=20.0: engine.parse_version(versions[str(exe)]))
    assert not engine.find_godot()["ok"]
    assert engine.find_godot(str(new))["ok"]
    # Remembered: found again without the argument.
    assert Path(engine.find_godot()["exe"]) == new


def test_missing_engine_explains(monkeypatch):
    out = engine.find_godot()
    assert not out["ok"] and "godot_get_engine" in out["hint"]


def test_install_zip_checks_sha512(tmp_path, monkeypatch):
    archive = tmp_path / "g.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("Godot_v4.7.2-stable_win64.exe", b"x")
        zf.writestr("Godot_v4.7.2-stable_win64_console.exe", b"y")
    bad = engine.install_zip(archive, expected_sha512="0" * 128)
    assert not bad["ok"] and "checksum" in bad["error"]
    monkeypatch.setattr(engine, "engine_version", lambda exe, timeout=20.0: engine.parse_version("4.7.2.stable.x"))
    good = engine.install_zip(archive, expected_sha512=hashlib.sha512(archive.read_bytes()).hexdigest())
    assert good["ok"] and good["exe"].endswith("_console.exe")


def test_install_zip_refuses_path_escape(tmp_path):
    archive = tmp_path / "evil.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("../escape.exe", b"x")
    out = engine.install_zip(archive, expected_sha512=hashlib.sha512(archive.read_bytes()).hexdigest())
    assert not out["ok"] and "unsafe" in out["error"]
