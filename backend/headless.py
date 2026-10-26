"""Engine jobs without an open editor: import, script checks, export."""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .constants import ADDON_DIR, HEADLESS_TIMEOUT_S

_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
_ERR_RE = re.compile(r"^SCRIPT ERROR: (?P<kind>[\w ]+?): (?P<msg>.*)$")
_AT_RE = re.compile(r"\((?P<file>res://[^:()]+):(?P<line>\d+)\)")
_NOT_FOUND_RE = re.compile(r"Identifier not found: (\w+)")
_SECTION_RE = re.compile(r"^\[([^\]]+)\]\s*$")
_SKIP_DIRS = {".godot", ".git", ".import"}


def run(engine: dict[str, Any], root: Path, args: list[str], timeout: float = HEADLESS_TIMEOUT_S) -> dict[str, Any]:
    """Run the console engine headless on ``root``; the whole process tree dies on timeout."""
    cmd = [engine["exe"], "--headless", "--path", str(root), *args]
    try:
        # One merged stream keeps errors next to the lines that caused them.
        proc = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
            errors="replace", timeout=timeout, creationflags=_NO_WINDOW,
        )
    except subprocess.TimeoutExpired as exc:
        return {"ok": False, "error": f"timed out after {timeout:.0f}s", "output": str(exc.stdout or "")[-4000:]}
    except OSError as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": proc.returncode == 0, "code": proc.returncode, "output": proc.stdout or ""}


def import_project(engine: dict[str, Any], root: Path) -> dict[str, Any]:
    """Import every asset (needed once before checks and exports on a fresh clone)."""
    res = run(engine, root, ["--import"])
    errors = [line for line in res.get("output", "").splitlines() if line.startswith("ERROR:")]
    return {"ok": (root / ".godot").is_dir() and "error" not in res, "errors": errors[:40], **({"error": res["error"]} if "error" in res else {})}


def autoload_names(root: Path) -> set[str]:
    names: set[str] = set()
    section = ""
    for line in (root / "project.godot").read_text(encoding="utf-8").splitlines():
        m = _SECTION_RE.match(line)
        if m:
            section = m.group(1)
        elif section == "autoload" and "=" in line:
            names.add(line.split("=", 1)[0].strip())
    return names


_CLASS_NAME_RE = re.compile(r"^class_name\s+(\w+)", re.MULTILINE)
_CACHED_CLASS_RE = re.compile(r'"class":\s*&"(\w+)"')


def stale_class_cache(root: Path, scripts: list[str] | None = None) -> bool:
    """True when a script declares a ``class_name`` Godot's global class cache lacks.

    ``--check-only`` resolves global classes from ``.godot/global_script_class_cache.cfg``,
    which only an editor scan or an import writes: a class added since then reads as
    "Identifier not found" in every script that uses it."""
    cache = root / ".godot" / "global_script_class_cache.cfg"
    try:
        known = set(_CACHED_CLASS_RE.findall(cache.read_text(encoding="utf-8")))
    except OSError:
        return True
    for res_path in scripts if scripts is not None else project_scripts(root):
        if not res_path.endswith(".gd"):
            continue
        try:
            text = (root / res_path[len("res://"):]).read_text(encoding="utf-8")
        except OSError:
            continue
        if any(name not in known for name in _CLASS_NAME_RE.findall(text)):
            return True
    return False


def parse_errors(output: str, autoloads: set[str] = frozenset()) -> list[dict[str, Any]]:
    """``SCRIPT ERROR: Parse Error: …`` + its ``at: … (res://x.gd:4)`` line → rows."""
    rows: list[dict[str, Any]] = []
    lines = output.splitlines()
    for i, line in enumerate(lines):
        m = _ERR_RE.match(line.strip())
        if not m:
            continue
        row: dict[str, Any] = {"kind": m.group("kind"), "message": m.group("msg").strip()}
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        at = _AT_RE.search(nxt)
        if at:
            row["file"], row["line"] = at.group("file"), int(at.group("line"))
        missing = _NOT_FOUND_RE.search(row["message"])
        if missing and missing.group(1) in autoloads:
            # --check-only compiles without the autoload singletons registered.
            row["maybe_autoload"] = True
        if row not in rows:
            rows.append(row)
    return rows


def project_scripts(root: Path, limit: int = 400) -> list[str]:
    out: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        rel = Path(dirpath).relative_to(root)
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS and not (rel == Path("addons") and d == ADDON_DIR)]
        for name in filenames:
            if name.endswith((".gd", ".gdshader")):
                out.append("res://" + (rel / name).as_posix().lstrip("./"))
                if len(out) >= limit:
                    return sorted(out)
    return sorted(out)


def validate_scripts(
    engine: dict[str, Any], root: Path, scripts: list[str], work_dir: Path | None = None
) -> dict[str, Any]:
    """Compile each GDScript with ``--check-only`` (real errors fail, autoload misses only
    warn) and every ``.gdshader`` in one engine run."""
    if not (root / ".godot").is_dir() or stale_class_cache(root):
        import_project(engine, root)
    autoloads = autoload_names(root)
    shaders = [s for s in scripts if s.endswith((".gdshader", ".gdshaderinc"))]
    scratch = work_dir or Path(tempfile.gettempdir()) / "godot-mcp"
    results = validate_shaders(engine, root, shaders, scratch) if shaders else []
    for script in (s for s in scripts if s not in shaders):
        path = script if script.startswith("res://") else "res://" + script.replace("\\", "/").lstrip("/")
        res = run(engine, root, ["--check-only", "--script", path], timeout=120)
        errors = parse_errors(res.get("output", ""), autoloads)
        if "error" in res:
            errors.append({"kind": "Run", "message": res["error"], "file": path})
        results.append({"script": path, "ok": not [e for e in errors if not e.get("maybe_autoload")], "errors": errors})
    failed = [r for r in results if not r["ok"]]
    return {"ok": not failed, "checked": len(results), "failed": len(failed), "results": failed or results[:20]}


# Run from the plugin's folder (never written into the project): loading a Shader compiles
# it, even on the headless dummy renderer, and prints SHADER ERROR lines. The marker goes to
# stderr like the errors, so each error stays after its shader's marker.
_SHADER_CHECK = """extends SceneTree

func _initialize() -> void:
\tfor p in OS.get_cmdline_user_args():
\t\tprinterr("DUCKY_SHADER ", p)
\t\tvar s := load(p) as Shader
\t\tif s != null:
\t\t\ts.get_shader_uniform_list()
\tquit()
"""
_SHADER_AT_RE = re.compile(r"\(:(\d+)\)")


def parse_shader_errors(output: str) -> dict[str, list[dict[str, Any]]]:
    """``DUCKY_SHADER res://x`` markers + ``SHADER ERROR`` / ``at: (null) (:N)`` → errors per shader."""
    found: dict[str, list[dict[str, Any]]] = {}
    current = ""
    lines = output.splitlines()
    for i, line in enumerate(lines):
        text = line.strip()
        if text.startswith("DUCKY_SHADER "):
            current = text[len("DUCKY_SHADER "):].strip()
            found.setdefault(current, [])
        elif current and text.startswith("SHADER ERROR: "):
            row: dict[str, Any] = {"kind": "Shader Error", "message": text[len("SHADER ERROR: "):], "file": current}
            at = _SHADER_AT_RE.search(lines[i + 1]) if i + 1 < len(lines) else None
            if at:
                row["line"] = int(at.group(1))
            found[current].append(row)
        elif current and text.startswith("ERROR: Cannot load shader"):
            found[current].append({"kind": "Load", "message": "file not found or unreadable", "file": current})
    return found


def validate_shaders(engine: dict[str, Any], root: Path, shaders: list[str], work_dir: Path) -> list[dict[str, Any]]:
    work_dir.mkdir(parents=True, exist_ok=True)
    checker = work_dir / "check_shaders.gd"
    checker.write_text(_SHADER_CHECK, encoding="utf-8", newline="\n")
    paths = [s if s.startswith("res://") else "res://" + s.replace("\\", "/").lstrip("/") for s in shaders]
    res = run(engine, root, ["--script", str(checker), "--", *paths], timeout=180)
    found = parse_shader_errors(res.get("output", ""))
    return [{"script": p, "ok": not found.get(p), "errors": found.get(p, [])} for p in paths]


def export_presets(root: Path) -> list[dict[str, Any]]:
    cfg = root / "export_presets.cfg"
    if not cfg.is_file():
        return []
    presets: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in cfg.read_text(encoding="utf-8").splitlines():
        m = _SECTION_RE.match(line)
        if m:
            current = None
            if re.fullmatch(r"preset\.\d+", m.group(1)):
                current = {}
                presets.append(current)
            continue
        if current is not None and "=" in line:
            key, val = line.split("=", 1)
            if key in ("name", "platform", "export_path", "runnable"):
                current[key] = val.strip().strip('"')
    return presets


def templates_dir(version: dict[str, Any]) -> Path:
    appdata = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    tag = f"{version['major']}.{version['minor']}" + (f".{version['patch']}" if version["patch"] else "")
    return appdata / "Godot" / "export_templates" / f"{tag}.{version['status']}"


def export(engine: dict[str, Any], root: Path, preset: str, output: str, *, debug: bool = False) -> dict[str, Any]:
    presets = export_presets(root)
    names = [p.get("name", "") for p in presets]
    if preset not in names:
        return {"ok": False, "error": f"no export preset {preset!r}", "presets": names}
    tdir = templates_dir(engine["version"])
    if not tdir.is_dir():
        return {
            "ok": False,
            "error": f"export templates {tdir.name} missing",
            "folder": str(tdir),
            "hint": "Editor → Manage Export Templates → Download, or unpack the .tpz into that folder.",
        }
    out = Path(output)
    if not out.is_absolute():
        out = root / out
    out.parent.mkdir(parents=True, exist_ok=True)
    res = run(engine, root, ["--export-debug" if debug else "--export-release", preset, str(out)], timeout=1800)
    errors = [line for line in res.get("output", "").splitlines() if line.startswith("ERROR:")]
    return {"ok": out.exists() and "error" not in res, "output": str(out), "errors": errors[:40], **({"error": res["error"]} if "error" in res else {})}
