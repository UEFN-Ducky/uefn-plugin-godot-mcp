---
description: "Godot UI: Control nodes, anchors and containers, CanvasLayer HUDs, Theme resources, buttons and signals"
metadata:
  label: "UI"
---

# UI (Control)

- HUD over a 3D/2D game: `CanvasLayer` → `Control` (full rect) → containers.
- Layout with **containers** (`VBoxContainer`, `HBoxContainer`, `MarginContainer`,
  `GridContainer`, `CenterContainer`) instead of hand-placed positions.
- Anchors: `set_anchor_preset {node_path, preset}` (full rect, center, top-left…).
- Size flags: `size_flags_horizontal = SIZE_EXPAND_FILL` to stretch inside containers.
- Fonts/colours: one `Theme` resource (`create_resource` type Theme) on the root Control;
  per-node tweaks with `add_theme_color_override("font_color", c)`.

## Main menu skeleton

```gdscript
extends Control

@onready var play_button: Button = %PlayButton
@onready var quit_button: Button = %QuitButton

func _ready() -> void:
	play_button.pressed.connect(_on_play)
	quit_button.pressed.connect(get_tree().quit)
	play_button.grab_focus()

func _on_play() -> void:
	get_tree().change_scene_to_file("res://main.tscn")
```

## HUD label bound to a signal

```gdscript
extends CanvasLayer

@onready var score_label: Label = %ScoreLabel

func set_score(value: int) -> void:
	score_label.text = "Score: %d" % value
```

- Text: `Label`, `RichTextLabel` (BBCode), `LineEdit` / `TextEdit` for input.
- Bars: `ProgressBar`, `TextureProgressBar`.
- Pause menus: set the menu's `process_mode = PROCESS_MODE_ALWAYS`, then `get_tree().paused = true`.
- Keyboard / gamepad navigation needs `grab_focus()` on the first control.
