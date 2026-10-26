"""Editors Ducky launched: one loopback port + this PC's bearer token per project."""

from __future__ import annotations

import json
import os
import secrets
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

from .constants import DEFAULT_PORT, EDITOR_READY_TIMEOUT_S, ENV_PORT, ENV_TOKEN, HTTP_HOST, PROBE_TIMEOUT_S
from .engine import state_dir

_LOCK = threading.Lock()


def token() -> str:
    """This PC's bearer token for editors Ducky starts (never written into a project)."""
    path = state_dir() / "token"
    with _LOCK:
        try:
            value = path.read_text(encoding="utf-8").strip()
        except OSError:
            value = ""
        if len(value) < 32:
            value = secrets.token_urlsafe(32)
            path.write_text(value, encoding="utf-8")
    return value


def port_open(port: int, host: str = HTTP_HOST) -> bool:
    try:
        with socket.create_connection((host, int(port)), timeout=PROBE_TIMEOUT_S):
            return True
    except OSError:
        return False


def free_port(start: int = DEFAULT_PORT, span: int = 50) -> int:
    for port in range(start, start + span):
        if not port_open(port):
            return port
    raise RuntimeError(f"no free port in {start}-{start + span - 1}")


def _sessions_file() -> Path:
    return state_dir() / "sessions.json"


def sessions() -> dict[str, dict[str, Any]]:
    try:
        data = json.loads(_sessions_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _save_sessions(data: dict[str, dict[str, Any]]) -> None:
    _sessions_file().write_text(json.dumps(data, indent=2), encoding="utf-8")


def _key(root: Path) -> str:
    return str(Path(root).resolve()).lower()


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform == "win32":
        import ctypes

        handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, int(pid))  # QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        code = ctypes.c_ulong()
        ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
        ctypes.windll.kernel32.CloseHandle(handle)
        return code.value == 259  # STILL_ACTIVE
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def live_session(root: Path | None = None) -> dict[str, Any] | None:
    """The running editor for ``root`` (or the newest live one), pruning dead entries."""
    data = sessions()
    alive = {k: v for k, v in data.items() if _pid_alive(int(v.get("pid") or 0))}
    if alive != data:
        _save_sessions(alive)
    if root is not None:
        return alive.get(_key(root))
    if not alive:
        return None
    return max(alive.values(), key=lambda v: float(v.get("started") or 0))


def url_for(port: int) -> str:
    return f"http://{HTTP_HOST}:{int(port)}/mcp"


def launch_editor(root: Path, engine: dict[str, Any], *, headless: bool = False) -> dict[str, Any]:
    """Start the Godot editor on ``root`` with the MCP addon's port and token in its env."""
    current = live_session(root)
    if current and port_open(int(current["port"])):
        return {"ok": True, "reused": True, **current}
    port = free_port()
    env = dict(os.environ)
    env[ENV_TOKEN] = token()
    env[ENV_PORT] = str(port)
    exe = engine["exe"] if headless else engine.get("editor_exe") or engine["exe"]
    args = [exe, "--editor", "--path", str(root)]
    if headless:
        args.insert(1, "--headless")
    log_path = state_dir() / "editor.log"
    flags = 0
    if sys.platform == "win32":
        flags = subprocess.CREATE_NEW_PROCESS_GROUP | getattr(subprocess, "DETACHED_PROCESS", 0)
    with log_path.open("ab") as log:
        proc = subprocess.Popen(
            args,
            cwd=str(root),
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            creationflags=flags,
            close_fds=True,
        )
    entry = {"project": str(root), "port": port, "pid": proc.pid, "started": time.time(), "headless": headless}
    data = sessions()
    data[_key(root)] = entry
    _save_sessions(data)
    deadline = time.time() + EDITOR_READY_TIMEOUT_S
    while time.time() < deadline:
        if port_open(port):
            return {"ok": True, "reused": False, **entry}
        if proc.poll() is not None:
            return {"ok": False, "error": f"Godot exited with code {proc.returncode}", "log": str(log_path)}
        time.sleep(0.5)
    return {
        "ok": False,
        "error": f"editor started but MCP port {port} did not open in {EDITOR_READY_TIMEOUT_S:.0f}s",
        "hint": "First open of a big project imports assets first; call godot_status again shortly.",
        "log": str(log_path),
        **entry,
    }


def stop_editor(root: Path) -> dict[str, Any]:
    entry = live_session(root)
    if not entry:
        return {"ok": True, "stopped": False}
    pid = int(entry.get("pid") or 0)
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)
    else:
        os.kill(pid, 15)
    data = sessions()
    data.pop(_key(root), None)
    _save_sessions(data)
    return {"ok": True, "stopped": True, "pid": pid}
