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


if __name__ == "__main__":
    test_check_target()
    test_check_zip_target()
    print("ok")
