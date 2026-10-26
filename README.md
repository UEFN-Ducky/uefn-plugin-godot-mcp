# GODOT MCP

Godot 4 editor control for [UEFN-Ducky](https://github.com/UEFN-Ducky/UEFN-Ducky)
(`godot-mcp`): 155 live editor tools through the bundled open-source
[Godot-MCP-Native](https://github.com/yurineko73/Godot-MCP-Native) addon, headless
script/shader checks and exports, and Godot's full class reference offline.
Install or update from the Store — do not install from a zip by hand.

## User flow

1. Install / enable **GODOT MCP**.
2. Ask Ducky to work on a Godot project (a folder with `project.godot`).

`godot_launch_editor` copies the addon into `addons/godot_mcp/`, enables it, imports
the project once if needed, and opens the editor with a loopback port and this PC's
bearer token in its environment (the token never lands in the project). No `mcp.json`
row, no Node.js, Python or uv for the person to install. No Godot on the PC: with the
person's OK, `godot_get_engine` fetches the pinned 4.7.2 once (SHA-512 checked); after
that everything runs offline.

## Agent tools

| Tool | Purpose |
|------|---------|
| `godot_status` | Engine, project, addon, editor, live tool count, `state` |
| `godot_launch_editor` / `godot_stop_editor` | Open / close the editor with MCP on |
| `godot_install_addon` / `godot_uninstall_addon` | Add / remove the addon (uninstall restores `project.godot`) |
| `godot_list_tools` | Live tool names; `names=` for schemas |
| `godot_call` | One editor tool; saved screenshots come back as image files |
| `godot_validate_script` | Headless GDScript + `.gdshader` compile, errors with lines |
| `godot_import` / `godot_export` | Headless import; export with a preset |
| `godot_api` / `godot_api_search` | Offline class reference (Godot 4.7.2, 1078 classes) |
| `godot_get_engine` | One verified engine download (asks the person first) |

Skill pack: `skills/godot` (router + 14 references; every sample compiles on 4.7.2).

## Vendored

- `backend/vendor/godot_mcp` — Godot-MCP-Native, MIT. Refresh with
  `py scripts/vendor_addon.py <clone> <sha>` (applies the Ducky patch; see
  `backend/vendor/UPSTREAM.md`).
- `backend/vendor/godot_docs` — Godot class reference, MIT. Rebuild with
  `py scripts/build_api_docs.py <godot checkout at a release tag> <version>`.

## Tests

```bash
py -m pytest backend -q
```

## Publish

```bash
py -3 scripts/release.py --publish --changelog "v0.1.0: GODOT MCP"
```

Requires `DUCKYOS_API_KEY`. Do not publish a dirty clone.

## License

MIT. Copyright (c) 2026 Mindful Path Company, LLC. See [LICENSE](LICENSE).
