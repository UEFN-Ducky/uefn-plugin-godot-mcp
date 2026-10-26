---
description: "Run and debug a Godot game from MCP: play, logs, runtime probe, runtime asserts, input simulation, breakpoints, screenshots, project tests"
metadata:
  label: "Testing and debugging"
---

# Testing and debugging

## Play loop

1. `godot_validate_script` on every changed script (exact lines, no editor needed).
2. `run_project {scene_path:"res://main.tscn", allow_window:true}`.
3. `await_scene_ready` (runtime probe) before poking the game.
4. Read: `get_runtime_scene_tree`, `inspect_runtime_node`, `evaluate_runtime_expression`.
5. Act: `simulate_runtime_input_action`, `call_runtime_node_method`, `update_runtime_node_property`.
6. Prove: `assert_runtime_condition {expression:"get_node('/root/main/Player').position.y > 1.0"}`
   or `await_runtime_condition`.
7. See: `get_runtime_screenshot {save_path:"user://run.png"}` (comes back as an image).
8. `get_editor_logs {source:"editor_panel"}` for prints, errors, warnings.
9. `stop_project {allow_window:true}`.

The addon registers an `MCPRuntimeProbe` autoload while it is enabled; runtime tools go
through it. `godot_uninstall_addon` removes it again.

## Debugger

`set_debugger_breakpoint` → run → `get_debug_stack_frames`, `get_debug_variables`,
`evaluate_debug_expression` → `debug_step_over` / `debug_continue`.

## Health checks

`detect_broken_scripts`, `scan_missing_resource_dependencies`, `audit_project_health`
after big refactors or moves.

## Project tests

`list_project_tests` / `run_project_tests {search_path:"res://test"}` find and run GUT
tests (and the addon's own format). A tiny self-check without a framework:

```gdscript
extends SceneTree

func _initialize() -> void:
	var ok := 2 + 2 == 4
	print("PASS" if ok else "FAIL")
	quit(0 if ok else 1)
```

Run headless with `godot --headless --path <project> --script res://test/check.gd`.
