#!/usr/bin/env python3
"""Copy Godot-MCP-Native's editor addon into backend/vendor/godot_mcp and apply the Ducky patch.

Usage:
  py scripts/vendor_addon.py <path to a Godot-MCP-Native clone> <commit sha>

The addon ships inside the plugin, so nothing is downloaded at runtime. The patch is a
few exact-text edits to mcp_server_native.gd: an editor that Ducky launches takes its
port and bearer token from the environment (the token never lands in the project),
starts its server on its own, and turns every tool on (upstream enables 30 of 155).
An anchor that no longer matches fails the run instead of shipping a half-patched addon.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Inside the backend package: a compiled build ships its data files next to the module.
DEST = ROOT / "backend" / "vendor" / "godot_mcp"
UPSTREAM = "yurineko73/Godot-MCP-Native"

ENV_HOOK = '''

## UEFN-Ducky (godot-mcp plugin): an editor that Ducky launches gets its port and
## bearer token from the environment, so the token never lands in the project, and
## every tool is turned on. A no-op when the editor was not started by Ducky.
func _apply_ducky_env() -> void:
\tvar token: String = OS.get_environment("DUCKY_GODOT_MCP_TOKEN")
\tif token.is_empty():
\t\treturn
\ttransport_mode = "http"
\tallow_remote = false
\tvar port: int = OS.get_environment("DUCKY_GODOT_MCP_PORT").to_int()
\tif port >= 1024 and port <= 65535:
\t\thttp_port = port
\t\t_native_server.set_http_port(port)
\tauth_enabled = true
\tauth_token = token
\tvar auth_manager: McpAuthManager = McpAuthManager.new()
\tauth_manager.set_token(token)
\tauth_manager.set_enabled(true)
\t_native_server.set_auth_manager(auth_manager)
\tfor tool_info in _native_server.get_registered_tools():
\t\t_native_server.set_tool_enabled(tool_info["name"], true)
\t_log_info("UEFN-Ducky launch: port " + str(http_port) + ", auth on, all tools on")
'''

# (anchor, replacement) pairs per addon file, each applied exactly once.
MAIN_PATCHES: list[tuple[str, str]] = [
    (
        "\telif auto_start:\n",
        '\telif auto_start or not OS.get_environment("DUCKY_GODOT_MCP_TOKEN").is_empty():\n',
    ),
    (
        "\t_apply_cmdline_overrides()\n\n\t_log_info(\"Starting native MCP server...\")",
        "\t_apply_cmdline_overrides()\n\t_apply_ducky_env()\n\n\t_log_info(\"Starting native MCP server...\")",
    ),
    (
        "func _stop_native_server() -> void:",
        ENV_HOOK.lstrip("\n") + "\nfunc _stop_native_server() -> void:",
    ),
]
# Upstream binds every interface even with allow_remote off (only its CLI route checks the
# peer): listen on loopback unless remote access was turned on.
HTTP_PATCHES: list[tuple[str, str]] = [
    (
        "\tvar error: Error = _tcp_server.listen(_port)\n",
        '\tvar error: Error = _tcp_server.listen(_port, "*" if _allow_remote else "127.0.0.1")\n',
    ),
]
PATCHES: dict[str, list[tuple[str, str]]] = {
    "mcp_server_native.gd": MAIN_PATCHES,
    "native_mcp/mcp_http_server_legacy.gd": HTTP_PATCHES,
}


def patch_text(text: str, patches: list[tuple[str, str]]) -> str:
    for anchor, replacement in patches:
        count = text.count(anchor)
        if count != 1:
            raise SystemExit(f"patch anchor found {count} times (want 1): {anchor[:60]!r}")
        text = text.replace(anchor, replacement)
    return text


def vendor(clone: Path, sha: str) -> None:
    src = clone / "addons" / "godot_mcp"
    if not (src / "plugin.cfg").is_file():
        raise SystemExit(f"not a Godot-MCP-Native clone: {clone}")
    if DEST.exists():
        shutil.rmtree(DEST)
    shutil.copytree(src, DEST, ignore=shutil.ignore_patterns("README.zh.md"))
    for rel, patches in PATCHES.items():
        path = DEST / rel
        path.write_text(patch_text(path.read_text(encoding="utf-8"), patches), encoding="utf-8", newline="\n")
    version = ""
    for line in (DEST / "plugin.cfg").read_text(encoding="utf-8").splitlines():
        if line.startswith("version="):
            version = line.split("=", 1)[1].strip().strip('"')
    (DEST.parent / "UPSTREAM.md").write_text(
        f"# Vendored: {UPSTREAM}\n\n"
        f"- Commit: `{sha}`\n"
        f"- Addon version: {version}\n"
        "- Path: `addons/godot_mcp` → `backend/vendor/godot_mcp` (without `README.zh.md`)\n"
        "- License: MIT (see `godot_mcp/LICENSE`)\n\n"
        "## Ducky patch (`scripts/vendor_addon.py`)\n\n"
        "`mcp_server_native.gd` gains `_apply_ducky_env()`: when the editor was started with\n"
        "`DUCKY_GODOT_MCP_TOKEN` (and `DUCKY_GODOT_MCP_PORT`), the server starts on its own, binds\n"
        "that loopback port, requires that bearer token and turns every tool on. Without the\n"
        "environment the addon behaves like upstream.\n\n"
        "`native_mcp/mcp_http_server_legacy.gd` listens on `127.0.0.1` unless `allow_remote` is on\n"
        "(upstream bound every interface even with remote access off).\n\n"
        "The addon's own **CLI Tools → Install** button downloads the gdmcp CLI from GitHub when\n"
        "a person presses it; Ducky never uses it.\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"vendored {UPSTREAM}@{sha} (addon {version}) into {DEST}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    vendor(Path(sys.argv[1]), sys.argv[2])
