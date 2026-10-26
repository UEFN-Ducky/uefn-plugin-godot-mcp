---
description: "GDScript 2.0 for Godot 4: typed code, annotations, signals, await, static typing, and the Godot 3 to 4 renames"
metadata:
  label: "GDScript"
---

# GDScript 2.0 (Godot 4)

## Shape of a script

```gdscript
class_name Player
extends CharacterBody3D

signal health_changed(new_health: int)
signal died

enum State { IDLE, RUN, JUMP }

const SPEED := 6.0

@export var max_health: int = 100
@export_range(0.0, 20.0, 0.5) var jump_velocity: float = 4.5
@export var weapon_scene: PackedScene

@onready var camera: Camera3D = $Head/Camera3D
@onready var anim: AnimationPlayer = %AnimationPlayer

var health: int = max_health:
	set(value):
		health = clampi(value, 0, max_health)
		health_changed.emit(health)
		if health == 0:
			died.emit()

var state: State = State.IDLE


func _ready() -> void:
	died.connect(_on_died)


func take_damage(amount: int) -> void:
	health -= amount


func _on_died() -> void:
	queue_free()
```

- Tabs for indentation (Godot's default); one class per file; `class_name` makes it global.
- Type everything: `var x: int`, `func f(a: float) -> Vector3:`; `:=` infers.
- `%Name` = scene-unique node (set "Access as Unique Name"); `$Path/To/Node` otherwise.
- Setters / getters are written inline under the variable (no `setget`).

## Signals

```gdscript
extends Node

signal scored(points: int)

func _ready() -> void:
	scored.connect(_on_scored)
	scored.connect(func(points: int) -> void: print("lambda got ", points))
	scored.emit(10)

func _on_scored(points: int) -> void:
	print(points)
```

`button.pressed.connect(_on_pressed)`, never `connect("pressed", self, "_on_pressed")`.
One-shot: `sig.connect(cb, CONNECT_ONE_SHOT)`. Bind args: `cb.bind(extra)`.

## await (coroutines)

```gdscript
extends Node

func flash() -> void:
	await get_tree().create_timer(0.5).timeout
	print("half a second later")
	await get_tree().process_frame
```

`await some_signal` / `await some_coroutine()`; `yield` does not exist in Godot 4.

## Godot 3 → 4 (never write the left column)

| Godot 3 | Godot 4 |
|---------|---------|
| `export var x = 1` | `@export var x := 1` |
| `onready var n = $N` | `@onready var n := $N` |
| `yield(obj, "sig")` | `await obj.sig` |
| `connect("sig", obj, "m")` | `sig.connect(obj.m)` |
| `emit_signal("sig", a)` | `sig.emit(a)` (both still work) |
| `KinematicBody(2D)` | `CharacterBody3D` / `CharacterBody2D` |
| `move_and_slide(vel, Vector3.UP)` | set `velocity`, call `move_and_slide()` |
| `Spatial` | `Node3D` |
| `instance()` | `instantiate()` |
| `rand_range(a, b)` | `randf_range(a, b)` |
| `.tool` keyword | `@tool` annotation |
| `PoolStringArray` | `PackedStringArray` |
| `OS.get_ticks_msec()` | `Time.get_ticks_msec()` |
| `get_tree().change_scene("x")` | `get_tree().change_scene_to_file("x")` |
| `deg2rad` / `rad2deg` | `deg_to_rad` / `rad_to_deg` |

## Static typing wins

- Typed arrays and dictionaries: `var enemies: Array[Enemy] = []`,
  `var scores: Dictionary[String, int] = {}`.
- `as` casts return null on mismatch: `var body := node as CharacterBody3D`.
- `is` checks type: `if body is Player:`.
- Warnings like "unused parameter" are silenced by prefixing `_`: `func _on_hit(_by: Node) -> void:`.

## Check it

`godot_validate_script(scripts="res://player.gd")` after every write; fix every reported
line. A `maybe_autoload` row is an autoload name the headless check can't see — fine.
