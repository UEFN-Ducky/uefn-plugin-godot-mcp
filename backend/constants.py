"""Shared constants for the GODOT MCP Store plugin."""

from __future__ import annotations

PLUGIN_ID = "godot-mcp"
GODOT_INTENT = r"\b(godot|gdscript|gdshader|tscn|tres|godot\s*mcp|project\.godot)\b"

# The editor addon (backend/vendor/godot_mcp, see its UPSTREAM.md) speaks MCP over HTTP.
HTTP_HOST = "127.0.0.1"
DEFAULT_PORT = 9080
ADDON_DIR = "godot_mcp"
ADDON_CFG = "res://addons/godot_mcp/plugin.cfg"
ENV_TOKEN = "DUCKY_GODOT_MCP_TOKEN"
ENV_PORT = "DUCKY_GODOT_MCP_PORT"

# Optional one-time engine download (a person asks for it); everything else is offline.
ENGINE_VERSION = "4.7.2"
ENGINE_ZIP = f"Godot_v{ENGINE_VERSION}-stable_win64.exe.zip"
ENGINE_URL = (
    f"https://github.com/godotengine/godot-builds/releases/download/{ENGINE_VERSION}-stable/{ENGINE_ZIP}"
)
# From the release's SHA512-SUMS.txt.
ENGINE_SHA512 = (
    "83decd58fdf67b9d657958a1ae6bf1929c20785315a81effe245874cdc57acb7"
    "09bf868e00778a96984338c1b29dafdb453c6847747694621c6ecf5da2259993"
)
# Linux builds of the same version, by CPU: (zip name, sha512 from the release's SHA512-SUMS.txt).
ENGINE_BASE_URL = f"https://github.com/godotengine/godot-builds/releases/download/{ENGINE_VERSION}-stable/"
ENGINE_LINUX = {
    "x86_64": (
        f"Godot_v{ENGINE_VERSION}-stable_linux.x86_64.zip",
        "9aa00f7a605200940bce3027a567b782f49bd8e940dd06ae9e987bd65aee1b14"
        "67edd56ed84fcdcbdd44354bf613bdbb4e5d2913e925850368e150c59ed54c65",
    ),
    "aarch64": (
        f"Godot_v{ENGINE_VERSION}-stable_linux.arm64.zip",
        "dd59918da086bd49bde2f5450b5e567ff8650cbde9abbd7b8f4ca1197ff8c609"
        "baa38834666d032deafb47099078d7822279e2a0e06e5665745468f26533e7e2",
    ),
}

PROBE_TIMEOUT_S = 0.5
CONNECT_TIMEOUT_S = 12.0
CALL_TIMEOUT_S = 120.0
HEADLESS_TIMEOUT_S = 300.0
EDITOR_READY_TIMEOUT_S = 90.0
