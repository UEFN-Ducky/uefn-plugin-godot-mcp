---
description: "Godot animation: AnimationPlayer tracks, AnimationTree state machines and blend spaces, Tween for code motion"
metadata:
  label: "Animation"
---

# Animation

| Tool | Use |
|------|-----|
| `AnimationPlayer` | Keyframed tracks on any property (and method / audio tracks) |
| `AnimationTree` | State machines, blend spaces for characters (drives an AnimationPlayer) |
| `Tween` | Short motion from code (UI pops, door slides, hit flashes) |

Imported GLB characters bring their clips in an `AnimationPlayer` (see `assets_bridge`).

## Play and react

```gdscript
extends CharacterBody3D

@onready var anim: AnimationPlayer = $AnimationPlayer

func _physics_process(_delta: float) -> void:
	var next := "run" if velocity.length() > 0.1 else "idle"
	if anim.current_animation != next and anim.has_animation(next):
		anim.play(next, 0.2)
```

## AnimationTree state machine

```gdscript
extends CharacterBody3D

@onready var tree: AnimationTree = $AnimationTree
@onready var playback: AnimationNodeStateMachinePlayback = tree.get("parameters/playback")

func jump() -> void:
	playback.travel("jump")

func set_speed(blend: float) -> void:
	tree.set("parameters/Locomotion/blend_position", blend)
```

Parameter paths are listed in the AnimationTree inspector (`get_inspector_properties`).

## Tween

```gdscript
extends Control

func pop() -> void:
	var tween := create_tween().set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	scale = Vector2(0.6, 0.6)
	tween.tween_property(self, "scale", Vector2.ONE, 0.25)
	tween.tween_callback(func() -> void: print("done"))
```

Live check: `play_runtime_animation`, `get_runtime_animation_state`,
`travel_runtime_animation_tree` while the game runs.
