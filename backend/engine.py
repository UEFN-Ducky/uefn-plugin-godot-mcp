"""Find the Godot engine on this PC, or fetch the pinned build once when a person asks."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

from .constants import ENGINE_SHA512, ENGINE_URL, ENGINE_VERSION, ENGINE_ZIP, PLUGIN_ID

_VERSION_RE = re.compile(r"^(\d+)\.(\d+)(?:\.(\d+))?\.(\w+)")
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def state_dir() -> Path:
    """The plugin's own folder on this PC (engine, token, API cache)."""
    try:
        from backend.uefn_plugins.store import appdata_uefn_plugins_dir

        root = appdata_uefn_plugins_dir() / PLUGIN_ID
    except Exception:
        local = os.environ.get("LOCALAPPDATA") or os.environ.get("HOME") or "."
        root = Path(local) / "UEFN-Ducky" / "uefn_plugins" / PLUGIN_ID
    root.mkdir(parents=True, exist_ok=True)
    return root


def engine_dir() -> Path:
    return state_dir() / "engine"


def _saved_path_file() -> Path:
    return state_dir() / "engine.json"


def remember_path(path: str) -> None:
    _saved_path_file().write_text(json.dumps({"path": path}), encoding="utf-8")


def _saved_path() -> str:
    try:
        return str(json.loads(_saved_path_file().read_text(encoding="utf-8")).get("path") or "")
    except (OSError, ValueError):
        return ""


def _prefer_console(exe: Path) -> Path:
    """On Windows the *_console.exe twin prints to our pipes; the GUI exe does not."""
    if exe.name.lower().endswith("_console.exe"):
        return exe
    twin = exe.with_name(exe.stem + "_console.exe")
    return twin if twin.is_file() else exe


def _gui_twin(exe: Path) -> Path:
    """The windowed exe next to a console one (the editor a person sees)."""
    name = exe.name
    if name.lower().endswith("_console.exe"):
        gui = exe.with_name(name[: -len("_console.exe")] + ".exe")
        if gui.is_file():
            return gui
    return exe


def _godot_exes_in(folder: Path) -> list[Path]:
    if not folder.is_dir():
        return []
    found = [p for p in folder.glob("Godot*.exe") if p.is_file()]
    found += [p for p in folder.glob("*/Godot*.exe") if p.is_file()]
    if sys.platform != "win32":
        found += [p for p in folder.glob("Godot*") if p.is_file() and os.access(p, os.X_OK)]
    # Newest version first; .NET (mono) builds after the standard ones.
    newest = sorted(found, key=lambda p: p.name, reverse=True)
    return sorted(newest, key=lambda p: "mono" in p.name.lower())


def candidates(explicit: str = "") -> list[Path]:
    """Every place a Godot exe may be, best first. Paths need not exist."""
    out: list[Path] = []
    for raw in (explicit, os.environ.get("GODOT_PATH", ""), os.environ.get("GODOT", ""), _saved_path()):
        if raw:
            out.append(Path(raw))
    for name in ("godot", "godot4", "Godot", "godot.exe"):
        hit = shutil.which(name)
        if hit:
            out.append(Path(hit))
    out += _godot_exes_in(engine_dir())
    home = Path.home()
    roots = [
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")),
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")),
    ]
    for root in roots:
        out += _godot_exes_in(root / "Steam" / "steamapps" / "common" / "Godot Engine")
        if root.is_dir():
            for folder in sorted(root.glob("Godot*"), reverse=True):
                out += _godot_exes_in(folder)
    out += _godot_exes_in(home / "scoop" / "apps" / "godot" / "current")
    local = Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local"))
    out += _godot_exes_in(local / "Microsoft" / "WinGet" / "Links")
    out += _godot_exes_in(local / "Programs" / "Godot")
    out += _godot_exes_in(home / "Desktop")
    out += _godot_exes_in(home / "Downloads")
    return out


def parse_version(text: str) -> dict[str, Any] | None:
    """``4.7.2.stable.official.ed1daf0bf`` → {major, minor, patch, status, text}."""
    line = (text or "").strip().splitlines()[-1:] or [""]
    m = _VERSION_RE.match(line[0].strip())
    if not m:
        return None
    return {
        "major": int(m.group(1)),
        "minor": int(m.group(2)),
        "patch": int(m.group(3) or 0),
        "status": m.group(4),
        "text": line[0].strip(),
    }


def engine_version(exe: Path, timeout: float = 20.0) -> dict[str, Any] | None:
    try:
        proc = subprocess.run(
            [str(exe), "--version"],
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=_NO_WINDOW,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return parse_version(proc.stdout)


def find_godot(explicit: str = "") -> dict[str, Any]:
    """First Godot 4.x that answers ``--version``. ``exe`` = console build for headless jobs,
    ``editor_exe`` = the windowed build a person sees."""
    seen: set[str] = set()
    tried: list[str] = []
    for cand in candidates(explicit):
        if not cand.is_file():
            continue
        exe = _prefer_console(cand)
        key = str(exe.resolve()).lower()
        if key in seen:
            continue
        seen.add(key)
        tried.append(str(exe))
        ver = engine_version(exe)
        if ver and ver["major"] >= 4:
            if explicit and Path(explicit).is_file():
                remember_path(str(cand))
            return {"ok": True, "exe": str(exe), "editor_exe": str(_gui_twin(exe)), "version": ver}
    return {
        "ok": False,
        "error": "Godot 4 not found",
        "tried": tried,
        "hint": f"Pass godot_path, set GODOT_PATH, or run godot_get_engine (one {ENGINE_VERSION} download).",
    }


def _sha512(path: Path) -> str:
    h = hashlib.sha512()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def install_zip(archive: Path, *, expected_sha512: str = ENGINE_SHA512) -> dict[str, Any]:
    """Check a downloaded engine zip and unpack it into the plugin's engine folder."""
    digest = _sha512(archive)
    if digest != expected_sha512:
        return {"ok": False, "error": "engine download checksum mismatch", "sha512": digest}
    dest = engine_dir() / ENGINE_VERSION
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as zf:
        for member in zf.namelist():
            target = (dest / member).resolve()
            if dest.resolve() not in target.parents and target != dest.resolve():
                return {"ok": False, "error": f"unsafe path in engine zip: {member}"}
        zf.extractall(dest)
    return find_godot(str(next(iter(_godot_exes_in(dest)), "")))


def fetch_engine() -> dict[str, Any]:
    """Download the pinned Godot build once (only when a person asks), then use it offline."""
    if sys.platform != "win32":
        return {"ok": False, "error": "auto download is Windows-only; install Godot and pass godot_path"}
    have = _godot_exes_in(engine_dir() / ENGINE_VERSION)
    if have:
        return find_godot(str(have[0]))
    archive = engine_dir() / ENGINE_ZIP
    archive.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(ENGINE_URL, headers={"User-Agent": "UEFN-Ducky-GODOT-MCP/0.1"})
    with urllib.request.urlopen(req, timeout=600) as resp, archive.open("wb") as fh:
        shutil.copyfileobj(resp, fh, 1 << 20)
    try:
        return install_zip(archive)
    finally:
        archive.unlink(missing_ok=True)
