---
description: "The 155 live Godot editor tools by domain, the call order that works, and the Vibe Coding flags"
metadata:
  label: "Editor tools"
---

# Editor tools (`godot_call`)

Always `godot_list_tools(names="...")` for the exact schema before the first call of a tool.

## A scene edit that works

```text
create_scene      {scene_path:"res://main.tscn", root_node_type:"Node3D"}   # saves, does NOT open
open_scene        {scene_path:"res://main.tscn", allow_ui_focus:true}
get_scene_tree    {}                                   # root path is /root/<root name>, e.g. /root/main
create_node       {parent_path:"/root/main", node_type:"CharacterBody3D", node_name:"Player"}
create_script     {script_path:"res://player.gd", content:"extends CharacterBody3D\n..."}
attach_script     {node_path:"/root/main/Player", script_path:"res://player.gd"}
add_resource      {node_path:"/root/main/Player", resource_type:"CollisionShape3D", resource_name:"Shape"}
update_node_property {node_path:"/root/main/Player", property_name:"position", property_value:{x:0,y:1,z:0}}
connect_signal    {emitter_path:"/root/main/Area", signal_name:"body_entered", receiver_path:"/root/main", receiver_method:"_on_area_body_entered"}
save_scene        {}
```

Several edits at once: `batch_scene_node_edits` / `batch_update_node_properties`
(one undo step).

## Domains

| Domain | Tools |
|--------|-------|
| Nodes | `create_node` `delete_node` `duplicate_node` `move_node` `rename_node` `update_node_property` `get_node_properties` `list_nodes` `get_scene_tree` `add_resource` `set_anchor_preset` |
| Signals / groups | `connect_signal` `disconnect_signal` `get_signals` `get_node_groups` `set_node_groups` `find_nodes_in_group` |
| Scenes | `create_scene` `open_scene` `save_scene` `get_current_scene` `get_scene_structure` `list_project_scenes` `list_open_scenes` `close_scene_tab` `audit_scene_node_persistence` `audit_scene_inheritance` |
| Scripts | `create_script` `read_script` `modify_script` `attach_script` `analyze_script` `list_project_scripts` `search_in_files` `list_project_script_symbols` `find_script_symbol_definition` `find_script_symbol_references` `rename_script_symbol` `open_script_at_line` |
| Editor | `get_editor_state` `get_selected_nodes` `select_node` `select_file` `get_inspector_properties` `set_editor_setting` `get_editor_screenshot` `reload_project` `execute_editor_script` |
| Run / logs | `run_project` `stop_project` `get_editor_logs` `clear_output` `get_performance_metrics` |
| Runtime (game running) | `get_runtime_scene_tree` `inspect_runtime_node` `update_runtime_node_property` `call_runtime_node_method` `evaluate_runtime_expression` `await_runtime_condition` `assert_runtime_condition` `simulate_runtime_input_action` `simulate_runtime_input_event` `get_runtime_screenshot` `play_runtime_animation` `set_runtime_shader_parameter` `set_runtime_tilemap_cell` … |
| Debugger | `set_debugger_breakpoint` `request_debug_break` `get_debug_stack_frames` `get_debug_variables` `debug_step_over` `debug_continue` `evaluate_debug_expression` … |
| Project | `get_project_info` `get_project_settings` `list_project_input_actions` `upsert_project_input_action` `list_project_autoloads` `list_project_global_classes` `get_class_api_metadata` `list_project_resources` `create_resource` `reimport_resources` `get_resource_dependencies` `scan_missing_resource_dependencies` `detect_broken_scripts` `audit_project_health` |
| Tests | `list_project_tests` `run_project_test` `run_project_tests` |
| Export | `list_export_presets` `validate_export_preset` `inspect_export_templates` `run_export` |

## Vibe Coding flags

The addon starts in Vibe Coding mode so it does not steal the person's focus:
`open_scene` needs `allow_ui_focus:true`; `run_project` / `stop_project` need
`allow_window:true`. The refusal text names the flag — add it and call again.

## Screenshots

`get_editor_screenshot {format:"png", save_path:"user://shot.png"}` (needs a windowed
editor) and `get_runtime_screenshot` save a file; `godot_call` returns it under
`images` as a real path so the chat shows it. `user://` lands in Godot's AppData folder,
which `view_image` cannot open: to look at a shot yourself, save it under `res://`
(e.g. `res://shots/run.png`) and delete the folder when done.

## Driving a running game

Key input: `simulate_runtime_input_event {event:{type:"key", physical_keycode:87, pressed:true}}`
(87 = W; send `pressed:false` to release). Read state with `evaluate_runtime_expression
{expression:"[score, get_tree().get_nodes_in_group('enemies').size()]", node_path:"/root/main"}`
and wait for outcomes with `await_runtime_condition {expression, timeout_ms}`.

## Escape hatch

`execute_editor_script` runs GDScript inside the editor (EditorScript-style). Use it
only when no tool covers the job, keep it small, and `save_scene` afterwards.
