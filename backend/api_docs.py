"""Offline Godot class reference (backend/vendor/godot_docs, built by scripts/build_api_docs.py)."""

from __future__ import annotations

import gzip
import json
import threading
from pathlib import Path
from typing import Any

DOCS_DIR = Path(__file__).resolve().parent / "vendor" / "godot_docs"
_SECTIONS = ("methods", "members", "signals", "constants", "constructors", "operators", "annotations", "theme_items")
_LOCK = threading.Lock()
_CACHE: dict[str, Any] = {}


def load(docs_dir: Path = DOCS_DIR) -> dict[str, Any]:
    key = str(docs_dir)
    with _LOCK:
        if key not in _CACHE:
            path = next(iter(sorted(docs_dir.glob("classes-*.json.gz"), reverse=True)), None)
            if path is None:
                raise FileNotFoundError(f"no class reference in {docs_dir}")
            with gzip.open(path, "rt", encoding="utf-8") as fh:
                _CACHE[key] = json.load(fh)
        return _CACHE[key]


def _find_class(classes: dict[str, Any], name: str) -> dict[str, Any] | None:
    if name in classes:
        return classes[name]
    low = name.lower()
    return next((c for n, c in classes.items() if n.lower() == low), None)


def _signature(row: dict[str, Any]) -> str:
    args = ", ".join(
        f"{a['name']}: {a['type']}" + (f" = {a['default']}" if "default" in a else "") for a in row.get("args", [])
    )
    sig = f"{row['name']}({args}) -> {row.get('return', 'void')}"
    return f"{sig} {row['qualifiers']}" if row.get("qualifiers") else sig


def _trim(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:limit].rstrip() + " …"


def lookup(class_name: str, member: str = "", *, docs_dir: Path = DOCS_DIR, max_rows: int = 40) -> dict[str, Any]:
    """One class: brief, description, inheritance chain and its members; ``member`` filters
    every section (methods, properties, signals, constants…) to names containing it."""
    data = load(docs_dir)
    classes = data["classes"]
    cls = _find_class(classes, (class_name or "").strip())
    if cls is None:
        hits = search(class_name, docs_dir=docs_dir, limit=8)["results"]
        return {"ok": False, "error": f"no class {class_name!r}", "did_you_mean": hits, "version": data["version"]}
    chain = []
    parent = cls.get("inherits", "")
    while parent and parent in classes and len(chain) < 20:
        chain.append(parent)
        parent = classes[parent].get("inherits", "")
    out: dict[str, Any] = {
        "ok": True,
        "version": data["version"],
        "class": cls["name"],
        "inherits": chain,
        "brief": cls.get("brief", ""),
    }
    needle = (member or "").strip().lower()
    if not needle:
        out["description"] = _trim(cls.get("description", ""), 2500)
        if cls.get("tutorials"):
            out["tutorials"] = cls["tutorials"]
    for section in _SECTIONS:
        rows = [r for r in cls.get(section, []) if not needle or needle in r["name"].lower()]
        if not rows:
            continue
        shaped = []
        for r in rows[:max_rows]:
            row: dict[str, Any] = {"name": r["name"]}
            if "args" in r:
                row["signature"] = _signature(r) if section != "signals" else f"{r['name']}({', '.join(a['name'] + ': ' + a['type'] for a in r['args'])})"
            for k in ("type", "default", "value", "enum"):
                if r.get(k):
                    row[k] = r[k]
            if r.get("description"):
                row["description"] = _trim(r["description"], 1200 if needle else 220)
            shaped.append(row)
        out[section] = shaped
        if len(rows) > max_rows:
            out[f"{section}_more"] = len(rows) - max_rows
    if needle and not any(s in out for s in _SECTIONS):
        out["note"] = f"{cls['name']} has no member matching {member!r} — check the inherits chain"
    return out


def search(query: str, *, docs_dir: Path = DOCS_DIR, limit: int = 25) -> dict[str, Any]:
    """Class and member names containing ``query`` (exact, then prefix, then substring)."""
    data = load(docs_dir)
    q = (query or "").strip().lower()
    if not q:
        return {"ok": False, "error": "query is required", "results": []}
    scored: list[tuple[int, str]] = []
    for name, cls in data["classes"].items():
        low = name.lower()
        if q in low:
            scored.append((0 if low == q else 1 if low.startswith(q) else 3, name))
        for section in _SECTIONS:
            for r in cls.get(section, []):
                rl = r["name"].lower()
                if q in rl:
                    scored.append((2 if rl == q else 4 if rl.startswith(q) else 5, f"{name}.{r['name']}"))
    scored.sort(key=lambda t: (t[0], len(t[1]), t[1]))
    return {"ok": True, "version": data["version"], "results": [n for _, n in scored[:limit]], "total": len(scored)}
