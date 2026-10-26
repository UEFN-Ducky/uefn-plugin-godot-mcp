---
description: "Ship a Godot build: export presets, export templates, godot_export headless, platform notes"
metadata:
  label: "Export"
---

# Export

1. `godot_export()` (no preset) lists the presets in `export_presets.cfg`.
2. No presets yet: create one in the editor (Project → Export → Add) or with
   `list_export_presets` / `validate_export_preset` live; Windows minimal preset:

```ini
[preset.0]

name="Windows Desktop"
platform="Windows Desktop"
runnable=true
export_filter="all_resources"
export_path="build/windows/game.exe"
```

3. `godot_export(preset="Windows Desktop")` → `--export-release` headless, output path
   from the preset (or `output=`). `debug=true` for a debug build.

## Export templates

Exports need templates matching the engine version exactly (`4.7.2.stable`). When
missing, `godot_export` names the folder
(`%APPDATA%\Godot\export_templates\4.7.2.stable`). The person installs them once:
Editor → Manage Export Templates → Download (about 1 GB), or unpack a `.tpz` there.
Ask before downloading; never pretend an export ran.

## Platform notes

- **Web:** Compatibility renderer; serve with COOP/COEP headers for threads, or turn
  threads off in the preset.
- **Android:** needs the Android SDK + a debug keystore configured in Editor Settings.
- **C# projects:** need the .NET Godot build and `dotnet` on the PC.
- `export_filter` / `exclude_filter` keep test scenes and the MCP addon out of shipped
  builds: add `addons/godot_mcp/*` to the exclude filter for release presets.
