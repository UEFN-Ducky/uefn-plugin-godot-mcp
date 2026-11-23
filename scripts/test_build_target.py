"""--target linux-*: refuses a machine that can't build it, and checks the built zip's python_abi.

    python scripts/test_build_target.py   (or pytest)
"""

from __future__ import annotations

import json
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_zip as bz  # noqa: E402


def _refused(fn, *args) -> bool:
    try:
        fn(*args)
    except SystemExit:
        return True
    return False


def test_check_target() -> None:
    bz.check_target("linux-x86_64", "linux", "x86_64")
    bz.check_target("linux-arm64", "linux", "aarch64")
    assert _refused(bz.check_target, "linux-arm64", "linux", "x86_64")
    assert _refused(bz.check_target, "linux-x86_64", "win32", "AMD64")
    assert _refused(bz.check_target, "linux-mips", "linux", "mips")


def test_check_zip_target() -> None:
    with tempfile.TemporaryDirectory() as td:
        z = Path(td) / "p.zip"
        for abi, target, ok in (
            ("cpython-313-x86_64-linux-gnu", "linux-x86_64", True),
            ("cpython-313-aarch64-linux-gnu", "linux-arm64", True),
            ("cp313-win_amd64", "linux-x86_64", False),
        ):
            with zipfile.ZipFile(z, "w") as zf:
                zf.writestr("plugin.json", json.dumps({"compiled": True, "python_abi": abi}))
            assert _refused(bz.check_zip_target, z, target) is not ok, (abi, target)


def test_zip_names() -> None:
    # release_platforms looks for deploy/*-<target>-compiled.ducky-plugin.zip; Windows stays as it was.
    assert bz.compiled_zip_name("p", "1.2.3", "linux-x86_64") == "p-1.2.3-linux-x86_64-compiled.ducky-plugin.zip"
    assert bz.compiled_zip_name("p", "1.2.3", "linux-arm64") == "p-1.2.3-linux-arm64-compiled.ducky-plugin.zip"
    assert bz.compiled_zip_name("p", "1.2.3") == "p-1.2.3-compiled.ducky-plugin.zip"


def test_linux_build_prunes_only_its_own_target() -> None:
    names = ["p-1-compiled", "p-0-linux-x86_64-compiled", "p-1-linux-x86_64-compiled", "p-1-linux-arm64-compiled"]
    old = bz.OUT_DIR
    with tempfile.TemporaryDirectory() as td:
        bz.OUT_DIR = Path(td)
        try:
            for n in names:
                (bz.OUT_DIR / f"{n}.ducky-plugin.zip").write_bytes(b"z")
            keep = bz.OUT_DIR / "p-1-linux-x86_64-compiled.ducky-plugin.zip"
            bz._prune_superseded_zips(keep, "*-linux-x86_64-compiled.ducky-plugin.zip")
            left = sorted(p.name for p in bz.OUT_DIR.iterdir())
        finally:
            bz.OUT_DIR = old
    assert left == sorted(f"{n}.ducky-plugin.zip" for n in names if n != "p-0-linux-x86_64-compiled"), left


if __name__ == "__main__":
    test_check_target()
    test_check_zip_target()
    test_zip_names()
    test_linux_build_prunes_only_its_own_target()
    print("ok")
