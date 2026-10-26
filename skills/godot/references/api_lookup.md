---
description: "Offline Godot class reference: godot_api and godot_api_search, and when to use the live get_class_api_metadata"
metadata:
  label: "API lookup"
---

# API lookup (offline)

The plugin ships Godot's own class reference (all 1078 classes of 4.7.2, MIT) — the
same text as the editor's help. No editor and no network needed.

| Tool | Use |
|------|-----|
| `godot_api(class_name)` | Brief, description, inheritance chain, every member (short) |
| `godot_api(class_name, member="slide")` | Only members whose name contains `slide`, full descriptions |
| `godot_api_search("body_entered")` | Which classes have it (`Area3D.body_entered`, …) |
| live `get_class_api_metadata` | Classes from the project or GDExtensions (not in the shipped reference) |

## Habits

- Look up before writing: `godot_api("CharacterBody3D", "move_and_slide")` →
  `move_and_slide() -> bool` (reads `velocity`, no argument in Godot 4).
- A member missing on a class is usually on a parent: the result's `inherits` chain
  tells you which class to ask next.
- Descriptions use Godot's BBCode (`[param x]`, `[method foo]`, `[code]`); read them as text.
- Signals come back as `signal_name(arg: Type)` — connect with `node.signal_name.connect(callable)`.
