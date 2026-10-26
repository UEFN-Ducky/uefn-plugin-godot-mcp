---
description: "Godot input: InputMap actions (project tools), polling vs events, mouse look, and simulated input while the game runs"
metadata:
  label: "Input"
---

# Input

## Actions first

Define actions instead of raw keys: `list_project_input_actions`,
`upsert_project_input_action {action_name:"jump", events:[...]}` (saves `project.godot`).
Read the schema for the event payload shape before the first call.

Common set: `move_left/right/forward/back`, `jump`, `interact`, `attack`, `pause`.

## Polling vs events

```gdscript
extends Node3D

@export var mouse_sensitivity: float = 0.002

func _ready() -> void:
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		rotate_y(-event.relative.x * mouse_sensitivity)
	if event.is_action_pressed("ui_cancel"):
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE

func _process(_delta: float) -> void:
	if Input.is_action_pressed("ui_accept"):
		pass
```

- Movement: poll in `_physics_process` (`Input.get_vector`, `get_axis`).
- One-off presses, menus, mouse look: `_unhandled_input` (UI gets first pick in `_gui_input`).

## Simulate input in a running game

`simulate_runtime_input_action {action_name:"jump", pressed:true}` then `pressed:false`;
`simulate_runtime_input_event` for keys / mouse. Assert the result with
`await_runtime_condition` / `assert_runtime_condition` (see `testing_debug`).
