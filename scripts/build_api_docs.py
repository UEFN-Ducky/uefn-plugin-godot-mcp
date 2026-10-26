#!/usr/bin/env python3
"""Pack Godot's class reference into backend/vendor/godot_docs/classes-<version>.json.gz.

Usage:
  py scripts/build_api_docs.py <godot source checkout at a release tag> <version>

Reads doc/classes, modules/*/doc_classes and platform/*/doc_classes (MIT, the same
XML the editor's help shows) and keeps names, signatures, defaults and descriptions,
so godot_api answers offline for that engine version.
"""

from __future__ import annotations

import gzip
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "backend" / "vendor" / "godot_docs"


def _text(node: ET.Element | None) -> str:
    if node is None or not node.text:
        return ""
    lines = [line.strip() for line in node.text.strip().splitlines()]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines))


def _args(node: ET.Element) -> list[dict[str, str]]:
    out = []
    for p in sorted(node.findall("param"), key=lambda e: int(e.get("index", "0"))):
        row = {"name": p.get("name", ""), "type": p.get("type", "")}
        if p.get("default") is not None:
            row["default"] = p.get("default", "")
        out.append(row)
    return out


def parse_class(path: Path) -> dict:
    root = ET.parse(path).getroot()
    cls: dict = {
        "name": root.get("name", path.stem),
        "inherits": root.get("inherits", ""),
        "brief": _text(root.find("brief_description")),
        "description": _text(root.find("description")),
    }
    tutorials = [t.text.strip() for t in root.findall("tutorials/link") if t.text]
    if tutorials:
        cls["tutorials"] = tutorials
    for tag, key in (("methods/method", "methods"), ("constructors/constructor", "constructors"),
                     ("operators/operator", "operators"), ("annotations/annotation", "annotations")):
        rows = []
        for m in root.findall(tag):
            ret = m.find("return")
            row = {"name": m.get("name", ""), "return": ret.get("type", "void") if ret is not None else "void",
                   "args": _args(m), "description": _text(m.find("description"))}
            if m.get("qualifiers"):
                row["qualifiers"] = m.get("qualifiers", "")
            rows.append(row)
        if rows:
            cls[key] = rows
    members = [{"name": m.get("name", ""), "type": m.get("type", ""), "default": m.get("default", ""),
                "description": _text(m)} for m in root.findall("members/member")]
    if members:
        cls["members"] = members
    signals = [{"name": s.get("name", ""), "args": _args(s), "description": _text(s.find("description"))}
               for s in root.findall("signals/signal")]
    if signals:
        cls["signals"] = signals
    constants = []
    for c in root.findall("constants/constant"):
        row = {"name": c.get("name", ""), "value": c.get("value", ""), "description": _text(c)}
        if c.get("enum"):
            row["enum"] = c.get("enum", "")
        constants.append(row)
    if constants:
        cls["constants"] = constants
    theme = [{"name": t.get("name", ""), "type": t.get("data_type", ""), "default": t.get("default", ""),
              "description": _text(t)} for t in root.findall("theme_items/theme_item")]
    if theme:
        cls["theme_items"] = theme
    return cls


def build(src: Path, version: str) -> Path:
    files = sorted(
        [*src.glob("doc/classes/*.xml"), *src.glob("modules/*/doc_classes/*.xml"), *src.glob("platform/*/doc_classes/*.xml")]
    )
    if not files:
        raise SystemExit(f"no class XML under {src}")
    classes = {}
    for path in files:
        cls = parse_class(path)
        classes[cls["name"]] = cls
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for old in OUT_DIR.glob("classes-*.json.gz"):
        old.unlink()
    dest = OUT_DIR / f"classes-{version}.json.gz"
    payload = json.dumps({"version": version, "classes": classes}, separators=(",", ":"), ensure_ascii=False)
    with gzip.open(dest, "wt", encoding="utf-8", compresslevel=9) as fh:
        fh.write(payload)
    (OUT_DIR / "SOURCE.md").write_text(
        f"# Godot class reference {version}\n\n"
        f"Built by `scripts/build_api_docs.py` from godotengine/godot tag `{version}-stable`\n"
        "(`doc/classes`, `modules/*/doc_classes`, `platform/*/doc_classes`).\n\n"
        "Godot Engine is MIT-licensed: Copyright (c) 2014-present Godot Engine contributors,\n"
        "(c) 2007-2014 Juan Linietsky, Ariel Manzur.\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"wrote {dest} ({len(classes)} classes, {dest.stat().st_size} bytes)")
    return dest


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    build(Path(sys.argv[1]), sys.argv[2])
