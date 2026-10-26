---
name: godot
description: "Build Godot 4 games through the GODOT MCP plugin: godot_status, godot_launch_editor, then godot_list_tools + godot_call for scenes, nodes, scripts, signals, debugging and play; godot_validate_script, godot_export and godot_api work without the editor and offline. Use for Godot, GDScript, .tscn/.tres, shaders or Godot exports."
license: MIT
metadata:
  label: GODOT MCP
  version: 1
  author: UEFN-Ducky
  copyright: Copyright 2026 Mindful Path Company, LLC
  allow_redistribute: true
  managed_by: uefn-ducky
  source_plugin_id: godot-mcp
---

# GODOT MCP — Godot 4 editor, headless jobs, offline API

You drive **Godot 4.x** (pinned build 4.7.2) through the **GODOT MCP** Store plugin.
Live editor tools are reached with `godot_list_tools` + `godot_call`, not as
separate `godot__*` entries. Headless tools (`godot_validate_script`, `godot_import`,
`godot_export`) and the class reference (`godot_api`, `godot_api_search`) need no
editor and no network.

**Godot work does NOT need the UEFN / Fortnite listener.** Never use Verse,
`spawn_actor` or island tools for a Godot project, and never Godot tools for an island.

## Start

1. `godot_status(project=...)` — read `state` before anything else.
2. `godot_launch_editor(project=...)` — installs the bundled addon, opens the editor
   with MCP on (one port per project, this PC's token). Reuses a running one.
3. `godot_list_tools()` → names; `godot_list_tools(names="create_node,attach_script")`
   → schemas. Never guess a tool or an argument name.
4. `godot_call(tool="...", arguments={...})`.

`project` defaults to the selected Ducky project when it holds `project.godot`.

| state | Meaning → do |
|-------|--------------|
| `missing_engine` | No Godot 4 found → ask the person for its path (`godot_path=`), or with their OK `godot_get_engine` (one ~86 MB download, then offline) |
| `no_project` | No `project.godot` → pass `project=` or create one (see `scenes_nodes`) |
| `addon_missing` / `waiting_for_editor` | `godot_launch_editor` |
| `ready` | List, then call |
| `error` | `godot_stop_editor`, then `godot_launch_editor` |

## Route — `skill_read_subskill("godot", "<id>")`

| Id | When |
|----|------|
| `connection` | States, ports, token, editors the person opened themselves |
| `editor_tools` | The 155 live tools by domain, call order, Vibe Coding flags |
| `api_lookup` | `godot_api` / `godot_api_search` before writing any engine call |
| `gdscript` | GDScript 2.0: typing, signals, await, Godot 3 → 4 renames |
| `scenes_nodes` | Scenes, owners, instancing, groups, autoloads, `.tscn`, new project |
| `physics` | CharacterBody2D/3D movement, layers/masks, Areas, raycasts |
| `input` | InputMap actions, `_unhandled_input`, simulated input |
| `animation` | AnimationPlayer, AnimationTree, Tween |
| `ui` | Control, anchors, containers, Theme |
| `shaders` | `.gdshader` spatial / canvas_item, uniforms |
| `rendering` | Renderers, WorldEnvironment, lights, GI |
| `testing_debug` | Run, logs, runtime probe, breakpoints, screenshots, asserts |
| `export` | Presets, templates, `godot_export` |
| `assets_bridge` | GLB / textures / audio in from Blender, Meshy, Tripo, UEFN |

## Hard rules

- **Read before writing:** `get_scene_tree` before any node path; `read_script` before
  `modify_script`; `godot_api` before any engine method you are not sure of.
- **Godot 4 only:** no `yield`, `onready var`, `export var`, `KinematicBody`,
  `move_and_slide(velocity)`, `connect("sig", obj, "method")`. See `gdscript`.
- **Check every script and shader you write:** `godot_validate_script(scripts="res://x.gd,res://fx.gdshader")`
  gives exact lines (the live `validate_script` only reports line 0).
- **Save** with `save_scene` after node edits; edits live only in the open scene until then.
- **Vibe Coding mode** is on: tools that focus a scene or open a game window need
  `allow_ui_focus=true` / `allow_window=true` in their arguments.
- Never write into `.godot/`; never edit `project.godot` by hand while the editor runs
  (use `get_project_settings` / input-map / autoload tools).

## Verify

`godot_validate_script` for code, `get_scene_tree` + the `.tscn` on disk for scenes,
`run_project` + `get_editor_logs` + `get_runtime_screenshot` for behaviour.
