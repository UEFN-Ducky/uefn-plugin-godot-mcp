from __future__ import annotations

import base64
from types import SimpleNamespace

import pytest

import backend
from backend import client, engine, runtime


@pytest.fixture(autouse=True)
def _isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(engine, "state_dir", lambda: tmp_path / "state")
    monkeypatch.setattr(runtime, "state_dir", lambda: tmp_path / "state")
    (tmp_path / "state").mkdir()
    monkeypatch.setattr(backend, "_selected_project", lambda: "")
    monkeypatch.setattr(runtime, "port_open", lambda port, host="": False)


def _engine_ok(monkeypatch):
    monkeypatch.setattr(engine, "find_godot", lambda path="": {"ok": True, "exe": "g", "version": {}})


def _project(tmp_path):
    root = tmp_path / "game"
    root.mkdir()
    (root / "project.godot").write_text('config/name="Game"\n', encoding="utf-8")
    return root


def test_missing_engine(monkeypatch):
    monkeypatch.setattr(engine, "find_godot", lambda path="": {"ok": False})
    assert backend.build_status()["state"] == "missing_engine"


def test_no_project(monkeypatch):
    _engine_ok(monkeypatch)
    assert backend.build_status()["state"] == "no_project"


def test_addon_missing_then_waiting(tmp_path, monkeypatch):
    _engine_ok(monkeypatch)
    root = _project(tmp_path)
    assert backend.build_status(str(root))["state"] == "addon_missing"
    from backend import projects

    projects.install_addon(root)
    assert backend.build_status(str(root))["state"] == "waiting_for_editor"


def test_ready_with_live_session(tmp_path, monkeypatch):
    _engine_ok(monkeypatch)
    root = _project(tmp_path)
    monkeypatch.setattr(runtime, "live_session", lambda root=None: {"project": str(root), "port": 9081})
    monkeypatch.setattr(runtime, "port_open", lambda port, host="": port == 9081)
    monkeypatch.setattr(client, "list_tools", lambda url, token: [{"name": "a"}, {"name": "b"}])
    status = backend.build_status(str(root))
    assert status["state"] == "ready" and status["tools"] == 2
    assert status["editor"]["url"] == "http://127.0.0.1:9081/mcp" and "token" not in status["editor"]


def test_coerce_arguments():
    assert backend.coerce_arguments('{"a": 1}') == {"a": 1}
    assert backend.coerce_arguments(None) == {}
    with pytest.raises(ValueError):
        backend.coerce_arguments("[1]")


def test_token_is_stable_and_long():
    first = runtime.token()
    assert len(first) >= 32 and runtime.token() == first


def test_images_are_saved_as_files(tmp_path):
    png = base64.b64encode(b"\x89PNG fake").decode()
    blocks = [SimpleNamespace(type="text", text="shot"), SimpleNamespace(type="image", data=png, mimeType="image/png")]
    text, images = client.flatten_content(blocks, tmp_path / "media")
    assert text == "shot" and len(images) == 1 and images[0].endswith(".png")
    assert (tmp_path / "media").joinpath(images[0].split("\\")[-1].split("/")[-1]).read_bytes() == b"\x89PNG fake"


def test_saved_screenshots_resolve_to_files(tmp_path, monkeypatch):
    root = _project(tmp_path)
    monkeypatch.setenv("APPDATA", str(tmp_path / "roaming"))
    shot = tmp_path / "roaming" / "Godot" / "app_userdata" / "Game" / "shot.png"
    shot.parent.mkdir(parents=True)
    shot.write_bytes(b"png")
    (root / "shots").mkdir()
    (root / "shots" / "a.jpg").write_bytes(b"jpg")
    text = '{"save_path":"user://shot.png","other":"res://shots/a.jpg","gone":"res://missing.png","script":"res://x.gd"}'
    assert backend.saved_images(root, text) == [str(shot), str(root / "shots" / "a.jpg")]


def test_401_reads_plainly():
    assert "token" in client.describe_error(RuntimeError("Client error '401 Unauthorized'"))
