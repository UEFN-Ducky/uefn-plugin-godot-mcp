---
description: "Godot scenes and nodes: new projects, scene composition, owner rules, instancing, groups, autoloads, .tscn text, UIDs"
metadata:
  label: "Scenes and nodes"
---

# Scenes and nodes

A scene (`.tscn`) is a saved node tree; scenes instance other scenes. Keep one
responsibility per scene (Player, Enemy, Level, HUD) and compose them in a Main scene.

## New project from nothing

Write `project.godot` (the editor fills the rest on first open), then `godot_launch_editor`:

```ini
; Engine configuration file.
config_version=5

[application]

config/name="My Game"
run/main_scene="res://main.tscn"
config/features=PackedStringArray("4.7", "Forward Plus")
```

Then `create_scene` res://main.tscn → `open_scene` (allow_ui_focus) → build → `save_scene`.

## Editor edits and `owner`

Nodes made by the MCP tools get their owner set, so they save. Nodes you create from
code inside the editor (`execute_editor_script`) must get `node.owner = scene_root`
or they vanish on save. `audit_scene_node_persistence` lists nodes that would not save.

## Instancing at runtime

```gdscript
extends Node3D

@export var bullet_scene: PackedScene  # or: const BULLET := preload("res://bullet.tscn")

func shoot(from: Transform3D) -> void:
	var bullet := bullet_scene.instantiate() as Node3D
	bullet.global_transform = from
	get_tree().current_scene.add_child(bullet)
```

`preload` for fixed paths (compile time), `load` / `ResourceLoader.load_threaded_request`
for dynamic or big ones. Free with `queue_free()`.

## Groups

`add_to_group("enemies")`; `get_tree().get_nodes_in_group("enemies")`;
`get_tree().call_group("enemies", "alert", position)`. In the editor: `set_node_groups`.

## Autoloads (singletons)

Project → Autoload, or `upsert`-style tools (`list_project_autoloads`; edit via
`get_project_settings` / `execute_editor_script`). An autoload named `Game` is reachable as
`Game` from every script. Good for: game state, save system, audio manager, scene switching.

## Scene switching

```gdscript
extends Node

func go_to_level(path: String) -> void:
	get_tree().change_scene_to_file(path)
```

## `.tscn` text (read-only habit)

```ini
[gd_scene format=3 uid="uid://c8scmlp3u6evd"]

[ext_resource type="Script" uid="uid://bso0cv6yq8a8i" path="res://player.gd" id="1_ig7tw"]

[node name="main" type="Node3D"]

[node name="Player" type="CharacterBody3D" parent="."]
script = ExtResource("1_ig7tw")
```

Prefer tools to hand edits. If you must hand-edit, keep `uid`s and `id`s consistent and
`reload_project` afterwards. Godot 4.4+ writes a `.uid` file next to every script and
shader: move them together (`filesystem` tools or the editor), never delete them.
