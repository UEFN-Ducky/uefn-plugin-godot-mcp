"""GODOT MCP — Store desktop plugin: live Godot 4 editor control, headless jobs, offline API."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .constants import DEFAULT_PORT, GODOT_INTENT, PLUGIN_ID


def register(api: Any) -> None:
    connect = getattr(api, "connection", None)
    if callable(connect):
        connect(_connection_row, label="Godot MCP", program="godot")

    def tool(fn: Any) -> Any:
        return api.tool(name=fn.__name__, intent=GODOT_INTENT, listener=False)(fn)

    @tool
    def godot_status(project: str = "", godot_path: str = "") -> str:
        """Godot readiness: engine found, project, addon installed, editor connected, live tool count."""
        return _dump(build_status(project, godot_path))

    @tool
    def godot_get_engine() -> str:
        """Download the pinned Godot 4.7.2 (Windows, checksum-verified) once, only when the person
        asked for it or agreed. After that every Godot tool works offline."""
        from . import engine

        try:
            return _dump(engine.fetch_engine())
        except Exception as exc:  # noqa: BLE001 — network / disk failures go back as text
            return _dump({"ok": False, "error": str(exc)})

    @tool
    def godot_install_addon(project: str = "") -> str:
        """Copy the bundled MCP editor addon into the project's addons/ and enable it. Idempotent."""
        from . import projects

        root, err = _project(project)
        return _dump(err or projects.install_addon(root))

    @tool
    def godot_uninstall_addon(project: str = "") -> str:
        """Remove the MCP editor addon from the project (folder, plugin entry, probe autoload)."""
        from . import projects, runtime

        root, err = _project(project)
        if err:
            return _dump(err)
        runtime.stop_editor(root)
        return _dump(projects.uninstall_addon(root))

    @tool
    def godot_launch_editor(project: str = "", headless: bool = False, godot_path: str = "") -> str:
        """Open the project in the Godot editor with the MCP addon on (installs it first if missing).
        Reuses an editor Ducky already started for it. headless=True runs it windowless."""
        from . import engine, projects, runtime

        root, err = _project(project)
        if err:
            return _dump(err)
        eng = engine.find_godot(godot_path)
        if not eng.get("ok"):
            return _dump(eng)
        from . import headless as jobs

        installed = projects.install_addon(root)
        if not installed.get("ok"):
            return _dump(installed)
        if runtime.live_session(root) is None and (installed.get("copied") or not (root / ".godot" / "imported").is_dir()):
            # The addon preloads its icon and uses class_name types: on a project the editor
            # never imported (or right after a copy) it fails to load unless imported first.
            installed["import"] = jobs.import_project(eng, root)
        result = runtime.launch_editor(root, eng, headless=headless)
        result["addon"] = installed
        return _dump(result)

    @tool
    def godot_stop_editor(project: str = "") -> str:
        """Close the editor Ducky started for the project (unsaved scene changes are lost)."""
        from . import runtime

        root, err = _project(project)
        return _dump(err or runtime.stop_editor(root))

    @tool
    def godot_list_tools(names: str = "", project: str = "") -> str:
        """Live editor tools. Without names: every tool's name and one-line summary. With names
        (comma-separated): those tools' full descriptions and input schemas. Never guess a name."""
        from . import client

        conn, err = _connection(project)
        if err:
            return _dump(err)
        try:
            tools = client.list_tools(conn["url"], conn["token"])
        except Exception as exc:  # noqa: BLE001
            return _dump({"ok": False, "error": str(exc), "status": build_status(project)})
        wanted = {n.strip() for n in (names or "").split(",") if n.strip()}
        if wanted:
            picked = [t for t in tools if t["name"] in wanted]
            missing = sorted(wanted - {t["name"] for t in picked})
            return _dump({"ok": not missing, "tools": picked, **({"unknown": missing} if missing else {})})
        rows = [{"name": t["name"], "summary": (t["description"] or "").strip().split("\n", 1)[0][:160]} for t in tools]
        return _dump({"ok": True, "count": len(rows), "tools": rows, "hint": "godot_list_tools(names=...) for schemas"})

    @tool
    def godot_call(tool: str, arguments: dict[str, Any] | str | None = None, project: str = "") -> str:
        """Call one live editor tool by name (see godot_list_tools) with its arguments object.
        Pictures (editor / runtime screenshots) come back as saved image paths."""
        from . import client, engine

        name = (tool or "").strip()
        if not name:
            return _dump({"ok": False, "error": "tool name is required"})
        try:
            args = coerce_arguments(arguments)
        except ValueError as exc:
            return _dump({"ok": False, "error": str(exc)})
        conn, err = _connection(project)
        if err:
            return _dump(err)
        try:
            result = client.call_tool(conn["url"], conn["token"], name, args, media_dir=engine.state_dir() / "media")
        except Exception as exc:  # noqa: BLE001
            return _dump({"ok": False, "tool": name, "error": str(exc), "status": build_status(project)})
        if conn.get("project"):
            saved = saved_images(Path(conn["project"]), result.get("text", ""))
            if saved:
                result["images"] = [*result.get("images", []), *saved]
        return _dump(result)

    @tool
    def godot_import(project: str = "", godot_path: str = "") -> str:
        """Headless asset import (run once on a fresh clone before checks or exports)."""
        from . import engine, headless

        root, err = _project(project)
        if err:
            return _dump(err)
        eng = engine.find_godot(godot_path)
        return _dump(headless.import_project(eng, root) if eng.get("ok") else eng)

    @tool
    def godot_validate_script(scripts: str = "", project: str = "", godot_path: str = "") -> str:
        """Compile GDScript and .gdshader files headless (no editor needed); errors come back with
        file and line. scripts: comma-separated res:// paths; empty = every script and shader."""
        from . import engine, headless

        root, err = _project(project)
        if err:
            return _dump(err)
        eng = engine.find_godot(godot_path)
        if not eng.get("ok"):
            return _dump(eng)
        wanted = [s.strip() for s in (scripts or "").split(",") if s.strip()] or headless.project_scripts(root)
        if not wanted:
            return _dump({"ok": True, "checked": 0, "note": "no .gd files"})
        return _dump(headless.validate_scripts(eng, root, wanted, engine.state_dir() / "checks"))

    @tool
    def godot_export(preset: str = "", output: str = "", debug: bool = False, project: str = "", godot_path: str = "") -> str:
        """Export a build with a preset from export_presets.cfg. Without preset: list the presets."""
        from . import engine, headless

        root, err = _project(project)
        if err:
            return _dump(err)
        if not preset:
            return _dump({"ok": True, "presets": headless.export_presets(root)})
        eng = engine.find_godot(godot_path)
        if not eng.get("ok"):
            return _dump(eng)
        if not output:
            match = next((p for p in headless.export_presets(root) if p.get("name") == preset), {})
            output = match.get("export_path") or f"build/{preset.replace(' ', '_')}"
        return _dump(headless.export(eng, root, preset, output, debug=debug))

    @tool
    def godot_api(class_name: str, member: str = "") -> str:
        """Offline Godot class reference: a class's brief, description, inheritance and members;
        member filters methods / properties / signals / constants by name. Use before writing calls."""
        from . import api_docs

        return _dump(api_docs.lookup(class_name, member))

    @tool
    def godot_api_search(query: str) -> str:
        """Find Godot classes and members by name in the offline class reference."""
        from . import api_docs

        return _dump(api_docs.search(query))

    api.log("GODOT MCP tools registered")


def unload() -> None:
    """Editors Ducky started keep running: closing them could drop unsaved work."""


def _dump(value: Any) -> str:
    return json.dumps(value, indent=2, default=str)


def coerce_arguments(arguments: Any) -> dict[str, Any]:
    """Accept a mapping or a JSON object string — models send both."""
    if arguments is None or arguments == "":
        return {}
    if isinstance(arguments, dict):
        return dict(arguments)
    if isinstance(arguments, str):
        try:
            parsed = json.loads(arguments)
        except json.JSONDecodeError as exc:
            raise ValueError(f"arguments is not valid JSON: {exc}") from exc
        if not isinstance(parsed, dict):
            raise ValueError("arguments must be a JSON object")
        return parsed
    raise ValueError("arguments must be an object")


_IMAGE_PATH_RE = re.compile(r"(?:res|user)://[^\"'\s]+?\.(?:png|jpe?g|webp)", re.IGNORECASE)


def saved_images(root: Path, text: str) -> list[str]:
    """Screenshot tools save to res:// or user://; hand back the real files so the chat shows them."""
    from . import projects

    out: list[str] = []
    for godot_path in dict.fromkeys(_IMAGE_PATH_RE.findall(text or "")):
        path = projects.resolve_path(root, godot_path)
        if path is not None and path.is_file():
            out.append(str(path))
    return out


def _selected_project() -> str:
    try:
        from backend.uefn_plugins.team_folders import current_project_root

        return current_project_root()
    except Exception:  # noqa: BLE001 — standalone tests have no host
        return ""


def _project(project: str = "") -> tuple[Path, dict[str, Any] | None]:
    from . import projects

    raw = (project or "").strip() or _selected_project()
    root = projects.project_root(raw) if raw else None
    if root is None:
        return Path("."), {
            "ok": False,
            "state": "no_project",
            "error": f"no Godot project (project.godot) at {raw!r}" if raw else "no Godot project given",
            "hint": "Pass project=<folder with project.godot>, or select that folder as the Ducky project.",
        }
    return root, None


def _connection(project: str = "") -> tuple[dict[str, Any], dict[str, Any] | None]:
    """URL + token of the editor to talk to: the one Ducky started for the project, else any
    editor Ducky started, else an editor the person opened with the addon's default port."""
    from . import runtime

    root = None
    if project or _selected_project():
        root_path, err = _project(project)
        root = None if err else root_path
    entry = (runtime.live_session(root) if root else None) or runtime.live_session()
    if entry and runtime.port_open(int(entry["port"])):
        return {"url": runtime.url_for(int(entry["port"])), "token": runtime.token(), "project": entry["project"]}, None
    if runtime.port_open(DEFAULT_PORT):
        return {"url": runtime.url_for(DEFAULT_PORT), "token": runtime.token(), "project": "", "external": True}, None
    return {}, {"ok": False, "state": "waiting_for_editor", "error": "no Godot editor with the MCP addon is running",
                "hint": "Call godot_launch_editor(project=...)."}


def _connection_row() -> dict[str, Any]:
    """Cheap port probe for the Connections menu."""
    from . import runtime

    entry = runtime.live_session()
    if entry and runtime.port_open(int(entry["port"])):
        return {"online": True, "detail": f"Connected · {Path(entry['project']).name} · port {entry['port']}"}
    return {"online": False, "detail": "Offline · godot_launch_editor opens a project"}


def build_status(project: str = "", godot_path: str = "") -> dict[str, Any]:
    from . import client, engine, projects, runtime

    eng = engine.find_godot(godot_path)
    out: dict[str, Any] = {"plugin_id": PLUGIN_ID, "engine": eng}
    root, err = _project(project)
    if err is None:
        out["project"] = {"root": str(root), "name": projects.project_name(root), "addon": projects.addon_status(root)}
    conn, cerr = _connection(project)
    if cerr is None:
        try:
            out["tools"] = len(client.list_tools(conn["url"], conn["token"]))
            out["editor"] = {k: v for k, v in conn.items() if k != "token"}
        except Exception as exc:  # noqa: BLE001
            out["editor_error"] = str(exc)

    if not eng.get("ok"):
        state, hint = "missing_engine", "Pass godot_path, set GODOT_PATH, or godot_get_engine (asks the person first)."
    elif "tools" in out:
        state, hint = "ready", "godot_list_tools, then godot_call. Headless: godot_validate_script, godot_export, godot_api."
    elif "editor_error" in out:
        state, hint = "error", "godot_stop_editor then godot_launch_editor."
    elif err is not None:
        state, hint = "no_project", err["hint"]
    elif not out["project"]["addon"]["installed"]:
        state, hint = "addon_missing", "godot_launch_editor installs the addon and opens the editor."
    else:
        state, hint = "waiting_for_editor", "godot_launch_editor(project=...) opens it with MCP on."
    out.update({"ok": state == "ready", "state": state, "hint": hint})
    return out
