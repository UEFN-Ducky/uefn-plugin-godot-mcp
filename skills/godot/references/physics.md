---
description: "Godot 4 physics: CharacterBody2D/3D movement templates, RigidBody, Areas, collision layers and masks, raycasts, Jolt"
metadata:
  label: "Physics"
---

# Physics

| Node | Use |
|------|-----|
| `CharacterBody3D/2D` | Player / NPC you move in code (`velocity` + `move_and_slide()`) |
| `RigidBody3D/2D` | Simulated objects (forces, impulses) |
| `StaticBody3D/2D` | Floors, walls |
| `Area3D/2D` | Triggers, pickups, damage zones (signals, no collision response) |
| `AnimatableBody3D` | Moving platforms driven by animation |

Every body needs a `CollisionShape3D/2D` child with a `shape` (or `CollisionPolygon`).
Godot 4.6+ projects use **Jolt** as the default 3D physics engine; 2D uses Godot Physics.

## 3D character (first/third person base)

```gdscript
extends CharacterBody3D

const SPEED := 5.0
const JUMP_VELOCITY := 4.5

func _physics_process(delta: float) -> void:
	if not is_on_floor():
		velocity += get_gravity() * delta
	if Input.is_action_just_pressed("ui_accept") and is_on_floor():
		velocity.y = JUMP_VELOCITY
	var input_dir := Input.get_vector("ui_left", "ui_right", "ui_up", "ui_down")
	var direction := (transform.basis * Vector3(input_dir.x, 0, input_dir.y)).normalized()
	if direction:
		velocity.x = direction.x * SPEED
		velocity.z = direction.z * SPEED
	else:
		velocity.x = move_toward(velocity.x, 0, SPEED)
		velocity.z = move_toward(velocity.z, 0, SPEED)
	move_and_slide()
```

## 2D platformer character

```gdscript
extends CharacterBody2D

const SPEED := 300.0
const JUMP_VELOCITY := -400.0

func _physics_process(delta: float) -> void:
	if not is_on_floor():
		velocity += get_gravity() * delta
	if Input.is_action_just_pressed("ui_accept") and is_on_floor():
		velocity.y = JUMP_VELOCITY
	var direction := Input.get_axis("ui_left", "ui_right")
	velocity.x = direction * SPEED if direction else move_toward(velocity.x, 0, SPEED)
	move_and_slide()
```

Replace `ui_*` with your own InputMap actions once they exist (see `input`).

## Areas

```gdscript
extends Area3D

func _ready() -> void:
	body_entered.connect(_on_body_entered)

func _on_body_entered(body: Node3D) -> void:
	if body.is_in_group("player"):
		body.call("collect_coin")
		queue_free()
```

## Layers and masks

`collision_layer` = what I am; `collision_mask` = what I detect. Name layers in Project
Settings → Layer Names (`get_project_settings`). Set in code with
`set_collision_layer_value(2, true)` (1-based).

## Raycasts

`RayCast3D` node (`is_colliding()`, `get_collider()`), or in code:

```gdscript
extends Node3D

func ground_below(from: Vector3) -> Dictionary:
	var query := PhysicsRayQueryParameters3D.create(from, from + Vector3.DOWN * 10.0)
	return get_world_3d().direct_space_state.intersect_ray(query)
```

Physics code goes in `_physics_process` (fixed tick), not `_process`.
