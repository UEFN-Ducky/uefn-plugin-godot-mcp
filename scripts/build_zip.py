#!/usr/bin/env python3
"""Zip plugin.json + backend (+ optional ui/) for Store upload. No secrets.

``--compiled`` builds through the UEFN Ducky build engine instead: the backend becomes a
Windows extension module (no Python source ships). release.py uses it for the Store.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import zipfile
import pathlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "deploy"


def _prune_superseded_zips(keep: pathlib.Path | None = None) -> None:
    """Delete every built zip except the one just built.

    deploy/ is gitignored build output; superseded zips are stale files that
    pile up one per version bump and can be re-created by re-running this
    script. Keeping them only invites installing an old build by mistake.
    """
    try:
        zips = sorted(OUT_DIR.glob("*.ducky-plugin.zip"))
    except OSError:
        return
    survivor = keep
    if survivor is None and zips:
        survivor = max(zips, key=lambda p: p.stat().st_mtime)
    for z in zips:
        try:
            if survivor is not None and z.samefile(survivor):
                continue
            z.unlink()
        except OSError:
            pass
SKIP_NAMES = {
    ".git",
    ".pytest_cache",
    "scripts",
    "deploy",
    ".gitignore",
    "README.md",
    "conftest.py",
    "__pycache__",
}
SKIP_SUFFIX = {".pyc", ".pyo", ".zip", ".ducky-plugin"}


def build_zip(*, out: Path | None = None) -> Path:
    manifest = json.loads((ROOT / "plugin.json").read_text(encoding="utf-8"))
    pid = str(manifest.get("id") or "").strip()
    version = manifest.get("version") or 1
    if not pid:
        raise SystemExit("plugin.json missing id")
    for path in ROOT.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".dat", ".env", ".pem", ".key"}:
            raise SystemExit(f"refusing to pack secret-looking file: {path}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dest = out or (OUT_DIR / f"{pid}-{version}.ducky-plugin.zip")
    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(ROOT.rglob("*")):
            if not path.is_file():
                continue
            rel_parts = path.relative_to(ROOT).parts
            if not rel_parts or any(part in SKIP_NAMES or part.startswith(".") for part in rel_parts):
                continue
            if path.suffix.lower() in SKIP_SUFFIX or path.name.startswith("."):
                continue
            if path.name.startswith("test_"):
                continue
            if path.name in SKIP_NAMES:
                continue
            zf.write(path, arcname="/".join(rel_parts))
    print(f"wrote {dest} ({dest.stat().st_size} bytes)")
    _prune_superseded_zips(dest)
    return dest


def _find_ducky_repo() -> Path:
    """Locate the UEFN-Ducky checkout that holds the build engine.

    ``DUCKY_REPO`` wins; otherwise try sibling checkouts next to this repo's parent.
    """
    candidates: list[Path] = []
    env = os.environ.get("DUCKY_REPO", "").strip()
    if env:
        candidates.append(Path(env))
    github = ROOT.parent.parent  # .../GitHub (this repo lives under uefn-plugins/)
    for name in ("UEFN-Ducky-Release", "UEFN-Ducky"):
        candidates.append(github / name)
    for cand in candidates:
        if (cand / "ducky_app" / "backend" / "uefn_plugins" / "compile.py").is_file():
            return cand
    raise SystemExit(
        "UEFN-Ducky checkout not found — set DUCKY_REPO to it (must contain "
        "ducky_app/backend/uefn_plugins/compile.py)."
    )


def _ducky_python(repo: Path) -> str:
    venv = repo / ".venv" / "Scripts" / "python.exe"
    return str(venv) if venv.is_file() else sys.executable


def build_compiled_zip(*, out: Path | None = None, release: bool = False) -> Path:
    """Build a compiled Store zip by invoking the Ducky build engine CLI.

    ``release`` bakes the Store license check in (with the Store's signing key), so a
    Store upload is never unlicensed.
    """
    manifest = json.loads((ROOT / "plugin.json").read_text(encoding="utf-8"))
    pid = str(manifest.get("id") or "").strip()
    version = manifest.get("version") or 1
    if not pid:
        raise SystemExit("plugin.json missing id")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dest = out or (OUT_DIR / f"{pid}-{version}-compiled.ducky-plugin.zip")
    repo = _find_ducky_repo()
    ducky_app = repo / "ducky_app"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ducky_app) + os.pathsep + env.get("PYTHONPATH", "")
    cmd = [_ducky_python(repo), "-m", "backend.uefn_plugins.compile", str(ROOT), str(dest)]
    if release:
        cmd.append("--release")
    print(f"compiling via {repo}")
    subprocess.run(cmd, cwd=str(ducky_app), env=env, check=True)
    print(f"wrote {dest} ({dest.stat().st_size} bytes)")
    _prune_superseded_zips(dest)
    return dest


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--compiled",
        action="store_true",
        help="compile the backend to a .pyd via the Ducky build engine (no Python source ships)",
    )
    args = ap.parse_args()
    if args.compiled:
        build_compiled_zip()
    else:
        _prune_superseded_zips(build_zip())
