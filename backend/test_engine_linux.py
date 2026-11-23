"""One-click engine download on Linux: the right build per CPU, a bad checksum refused and deleted,
Windows still on its .exe zip. A local HTTP server stands in for GitHub."""

from __future__ import annotations

import hashlib
import http.server
import io
import os
import platform
import sys
import threading
import zipfile

import pytest

from backend import constants, engine

BIN = "Godot_v4.7.2-stable_linux.x86_64"
FAKE_GODOT = b"#!/bin/sh\necho 4.7.2.stable.official.ed1daf0bf\n"


@pytest.fixture
def server(tmp_path):
    root = tmp_path / "www"
    root.mkdir()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(BIN, FAKE_GODOT)
    (root / f"{BIN}.zip").write_bytes(buf.getvalue())

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=str(root), **k)

        def log_message(self, *a):
            pass

    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}/", hashlib.sha512(buf.getvalue()).hexdigest()
    httpd.shutdown()


@pytest.fixture
def linux(tmp_path, monkeypatch, server):
    base, sha = server
    monkeypatch.setattr(engine, "state_dir", lambda: tmp_path / "state")
    monkeypatch.setattr(engine.sys, "platform", "linux")
    monkeypatch.setattr(platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(engine, "ENGINE_BASE_URL", base)
    monkeypatch.setattr(engine.shutil, "which", lambda name: None)
    monkeypatch.delenv("GODOT_PATH", raising=False)
    monkeypatch.delenv("GODOT", raising=False)
    return sha


def test_build_per_cpu_and_windows_unchanged():
    assert engine.linux_asset("x86_64")[0] == "Godot_v4.7.2-stable_linux.x86_64.zip"
    assert engine.linux_asset("AMD64")[0] == "Godot_v4.7.2-stable_linux.x86_64.zip"
    arm = engine.linux_asset("aarch64")
    assert arm[0] == "Godot_v4.7.2-stable_linux.arm64.zip" and engine.linux_asset("arm64") == arm
    assert arm[1] == constants.ENGINE_BASE_URL + arm[0] and len(arm[2]) == 128
    assert engine.linux_asset("riscv64") is None
    assert constants.ENGINE_ZIP == "Godot_v4.7.2-stable_win64.exe.zip"
    assert constants.ENGINE_URL == constants.ENGINE_BASE_URL + constants.ENGINE_ZIP


def test_bad_checksum_is_refused_and_deleted(linux, tmp_path, monkeypatch):
    monkeypatch.setattr(engine, "ENGINE_LINUX", {"x86_64": (f"{BIN}.zip", "0" * 128)})
    out = engine.fetch_engine()
    assert out["ok"] is False and "checksum mismatch" in out["error"]
    left = list((tmp_path / "state" / "engine").rglob("*"))
    assert left == [], left


def test_unknown_cpu_says_so(linux, monkeypatch):
    monkeypatch.setattr(platform, "machine", lambda: "riscv64")
    out = engine.fetch_engine()
    assert out["ok"] is False and "riscv64" in out["error"]


@pytest.mark.skipif(os.name == "nt", reason="runs the fake Linux binary")
def test_install_makes_the_binary_runnable(linux, tmp_path, monkeypatch):
    monkeypatch.setattr(engine, "ENGINE_LINUX", {"x86_64": (f"{BIN}.zip", linux)})
    out = engine.fetch_engine()
    exe = tmp_path / "state" / "engine" / "4.7.2" / BIN
    assert out["ok"] is True and out["exe"] == str(exe), out
    assert os.access(exe, os.X_OK)
    assert not (tmp_path / "state" / "engine" / f"{BIN}.zip").exists()
    assert engine.fetch_engine()["exe"] == str(exe)  # second ask reuses it, no download


def test_windows_still_uses_its_zip(tmp_path, monkeypatch):
    monkeypatch.setattr(engine.sys, "platform", "win32")
    seen = []

    def no_network(req, timeout):
        seen.append(req.full_url)
        raise OSError("no network in tests")

    monkeypatch.setattr(engine.urllib.request, "urlopen", no_network)
    monkeypatch.setattr(engine, "engine_dir", lambda: tmp_path / "engine")
    with pytest.raises(OSError):
        engine.fetch_engine()
    assert seen == [constants.ENGINE_URL] and seen[0].endswith("_win64.exe.zip")
    assert sys.platform == "win32"
