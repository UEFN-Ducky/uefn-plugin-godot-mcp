# Vendored: yurineko73/Godot-MCP-Native

- Commit: `eef4807190e7765e69d59c9e707d0ba170f6770d`
- Addon version: 1.0.8
- Path: `addons/godot_mcp` → `backend/vendor/godot_mcp` (without `README.zh.md`)
- License: MIT (see `godot_mcp/LICENSE`)

## Ducky patch (`scripts/vendor_addon.py`)

`mcp_server_native.gd` gains `_apply_ducky_env()`: when the editor was started with
`DUCKY_GODOT_MCP_TOKEN` (and `DUCKY_GODOT_MCP_PORT`), the server starts on its own, binds
that loopback port, requires that bearer token and turns every tool on. Without the
environment the addon behaves like upstream.

`native_mcp/mcp_http_server_legacy.gd` listens on `127.0.0.1` unless `allow_remote` is on
(upstream bound every interface even with remote access off).

The addon's own **CLI Tools → Install** button downloads the gdmcp CLI from GitHub when
a person presses it; Ducky never uses it.
