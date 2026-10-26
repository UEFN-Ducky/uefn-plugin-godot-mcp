"""Godot projects: find one, install / remove the vendored MCP addon, read its settings."""

from __future__ import annotations

import hashlib
import re
import shutil
from pathlib import Path
from typing import Any

from .constants import ADDON_CFG, ADDON_DIR

VENDOR = Path(__file__).resolve().parent / "vendor" / ADDON_DIR
STAMP = ".ducky_version"
PROBE_AUTOLOAD = "MCPRuntimeProbe"

_SECTION_RE = re.compile(r"^\[([^\]]+)\]\s*$")
_ENABLED_RE = re.compile(r"^enabled\s*=\s*PackedStringArray\((.*)\)\s*$")
_QUOTED_RE = re.compile(r'"((?:[^"\\]|\\.)*)"')


def project_root(path: str | Path) -> Path | None:
    """The folder holding ``project.godot``: the path itself, a parent, or one level down."""
    if not path:
        return None
    start = Path(path).expanduser()
    if start.is_file():
        start = start.parent
    for folder in (start, *start.parents):
        if (folder / "project.godot").is_file():
            return folder
    if start.is_dir():
        for child in sorted(start.iterdir()):
            if (child / "project.godot").is_file():
                return child
    return None


def project_name(root: Path) -> str:
    return _setting(root, "config/name") or root.name


def _setting(root: Path, key: str) -> str:
    for line in _read(root).splitlines():
        if line.startswith(key + "="):
            return line.split("=", 1)[1].strip().strip('"')
    return ""


def user_dir(root: Path) -> Path:
    """Where ``user://`` points for this project (Godot's app_userdata rules, Windows/Linux/macOS)."""
    import os
    import sys

    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    if _setting(root, "application/config/use_custom_user_dir") == "true":
        custom = _setting(root, "application/config/custom_user_dir_name")
        return base / (custom or project_name(root))
    return base / "Godot" / "app_userdata" / (project_name(root) or "[unnamed project]")


def resolve_path(root: Path, godot_path: str) -> Path | None:
    """``res://`` / ``user://`` → a file on disk (None for anything else)."""
    if godot_path.startswith("res://"):
        return root / godot_path[len("res://"):]
    if godot_path.startswith("user://"):
        return user_dir(root) / godot_path[len("user://"):]
    return None


def _read(root: Path) -> str:
    return (root / "project.godot").read_text(encoding="utf-8")


def _write(root: Path, text: str) -> None:
    (root / "project.godot").write_text(text, encoding="utf-8", newline="\n")


def vendor_stamp() -> str:
    """Content hash of the vendored addon: reinstall only when it changed."""
    h = hashlib.sha1()
    for path in sorted(VENDOR.rglob("*")):
        if path.is_file():
            h.update(path.relative_to(VENDOR).as_posix().encode())
            h.update(path.read_bytes())
    return h.hexdigest()[:16]


def enabled_plugins(text: str) -> list[str]:
    section = ""
    for line in text.splitlines():
        m = _SECTION_RE.match(line)
        if m:
            section = m.group(1)
            continue
        if section == "editor_plugins":
            em = _ENABLED_RE.match(line.strip())
            if em:
                return _QUOTED_RE.findall(em.group(1))
    return []


def set_enabled_plugins(text: str, plugins: list[str]) -> str:
    """Rewrite ``[editor_plugins] enabled=...``; drop the section when the list is empty."""
    value = "enabled=PackedStringArray(" + ", ".join(f'"{p}"' for p in plugins) + ")"
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines) if line.strip() == "[editor_plugins]"), -1)
    if start < 0:
        if not plugins:
            return text
        tail = "" if text.endswith("\n") or not text else "\n"
        return text + tail + "\n[editor_plugins]\n\n" + value + "\n"
    end = next((i for i in range(start + 1, len(lines)) if _SECTION_RE.match(lines[i])), len(lines))
    body = lines[start + 1 : end]
    idx = next((i for i, line in enumerate(body) if _ENABLED_RE.match(line.strip())), -1)
    if plugins:
        if idx >= 0:
            body[idx] = value
        else:
            body = ["", value, ""]
        new = lines[:start + 1] + body + lines[end:]
    else:
        if idx >= 0:
            del body[idx]
        if any(line.strip() for line in body):
            new = lines[:start + 1] + body + lines[end:]
        else:
            # Section only held our entry: remove it with the blank line before it.
            head = lines[:start]
            if head and not head[-1].strip():
                head = head[:-1]
            new = head + lines[end:]
    out = "\n".join(new)
    return out + "\n" if text.endswith("\n") else out


def _drop_probe_autoload(text: str) -> str:
    """The addon registers its runtime probe autoload; remove it with the addon."""
    lines = text.splitlines()
    keep = [line for line in lines if not line.startswith(f"{PROBE_AUTOLOAD}=")]
    if len(keep) == len(lines):
        return text
    start = next((i for i, line in enumerate(keep) if line.strip() == "[autoload]"), -1)
    if start >= 0:
        end = next((i for i in range(start + 1, len(keep)) if _SECTION_RE.match(keep[i])), len(keep))
        if not any(line.strip() for line in keep[start + 1 : end]):
            head = keep[:start]
            if head and not head[-1].strip():
                head = head[:-1]
            keep = head + keep[end:]
    out = "\n".join(keep)
    return out + "\n" if text.endswith("\n") else out


def addon_status(root: Path) -> dict[str, Any]:
    dest = root / "addons" / ADDON_DIR
    stamp = (dest / STAMP).read_text(encoding="utf-8").strip() if (dest / STAMP).is_file() else ""
    return {
        "installed": (dest / "plugin.cfg").is_file(),
        "enabled": ADDON_CFG in enabled_plugins(_read(root)),
        "current": bool(stamp) and stamp == vendor_stamp(),
    }


def install_addon(root: Path) -> dict[str, Any]:
    """Copy the vendored addon into ``addons/godot_mcp`` and enable it. Idempotent."""
    if not (root / "project.godot").is_file():
        return {"ok": False, "error": f"no project.godot in {root}"}
    dest = root / "addons" / ADDON_DIR
    stamp = vendor_stamp()
    copied = False
    if not ((dest / STAMP).is_file() and (dest / STAMP).read_text(encoding="utf-8").strip() == stamp):
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(VENDOR, dest)
        (dest / STAMP).write_text(stamp, encoding="utf-8")
        copied = True
    text = _read(root)
    plugins = enabled_plugins(text)
    enabled_now = False
    if ADDON_CFG not in plugins:
        _write(root, set_enabled_plugins(text, [*plugins, ADDON_CFG]))
        enabled_now = True
    return {"ok": True, "project": str(root), "copied": copied, "enabled_now": enabled_now, "stamp": stamp}


def uninstall_addon(root: Path) -> dict[str, Any]:
    if not (root / "project.godot").is_file():
        return {"ok": False, "error": f"no project.godot in {root}"}
    text = _read(root)
    plugins = [p for p in enabled_plugins(text) if p != ADDON_CFG]
    _write(root, _drop_probe_autoload(set_enabled_plugins(text, plugins)))
    dest = root / "addons" / ADDON_DIR
    removed = dest.exists()
    if removed:
        shutil.rmtree(dest)
    return {"ok": True, "project": str(root), "removed": removed}
