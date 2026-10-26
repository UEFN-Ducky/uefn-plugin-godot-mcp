---
description: "How GODOT MCP reaches the Godot editor: bundled addon, per-project port, bearer token, states and recovery"
metadata:
  label: "Connection"
---

# Connection

GODOT MCP bundles the open-source **Godot-MCP-Native** editor addon (pure GDScript,
MIT). `godot_launch_editor` copies it into `res://addons/godot_mcp/`, enables it in
`project.godot`, and starts the editor with two environment variables:

| Variable | Meaning |
|----------|---------|
| `DUCKY_GODOT_MCP_PORT` | Loopback port for this project (9080 upward, first free) |
| `DUCKY_GODOT_MCP_TOKEN` | This PC's bearer token (kept in the plugin's AppData) |

With them the addon starts its MCP server on its own, refuses calls without the
token (HTTP 401) and turns on all 155 tools. Nothing secret is written into the
project folder. Without them (a person opened Godot themselves) the addon behaves
like upstream: off until its **MCP** main-screen tab → Start, port 9080.

## Tools

| Tool | Use |
|------|-----|
| `godot_status(project)` | Engine, project, addon, editor, live tool count, `state` + `hint` |
| `godot_launch_editor(project, headless=False)` | Install addon + open editor (reuses a running one) |
| `godot_stop_editor(project)` | Close the editor Ducky started (unsaved edits are lost — `save_scene` first) |
| `godot_install_addon` / `godot_uninstall_addon` | Add / remove the addon (uninstall restores `project.godot`) |
| `godot_get_engine` | One verified Godot 4.7.2 download — only with the person's OK |

## Recovery

- `waiting_for_editor` after a launch: the first open of a big project imports
  assets first. Call `godot_status` again; do not relaunch in a loop.
- `error` / 401: `godot_stop_editor` then `godot_launch_editor` (fresh token + port).
- A Godot the person opened themselves on port 9080 with the addon's auth off still
  answers; the status shows `editor.external: true`.
- `headless=True` gives a windowless editor (CI, or when the person is not watching).
  Editor screenshots need a window: launch without `headless` for those.
