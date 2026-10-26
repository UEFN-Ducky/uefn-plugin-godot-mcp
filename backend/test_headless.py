from __future__ import annotations

from backend import headless

# Captured from Godot 4.7.2 `--headless --check-only --script`.
BROKEN = """Godot Engine v4.7.2.stable.official.ed1daf0bf - https://godotengine.org
SCRIPT ERROR: Parse Error: Cannot assign a value of type "String" as "int".
   at: GDScript::reload (res://broken.gd:4)
SCRIPT ERROR: Parse Error: Identifier "undefined_thing" not declared in the current scope.
   at: GDScript::reload (res://broken.gd:5)
ERROR: Failed to load script "res://broken.gd" with error "Parse error".
   at: load (modules/gdscript/gdscript_resource_format.cpp:46)
"""
AUTOLOAD = """SCRIPT ERROR: Compile Error: Identifier not found: Game
   at: GDScript::reload (res://auto.gd:4)
"""


def test_parse_errors():
    rows = headless.parse_errors(BROKEN)
    assert rows == [
        {"kind": "Parse Error", "message": 'Cannot assign a value of type "String" as "int".', "file": "res://broken.gd", "line": 4},
        {"kind": "Parse Error", "message": 'Identifier "undefined_thing" not declared in the current scope.', "file": "res://broken.gd", "line": 5},
    ]


def test_autoload_miss_is_flagged_not_failed():
    rows = headless.parse_errors(AUTOLOAD, {"Game"})
    assert rows[0]["maybe_autoload"] is True
    assert "maybe_autoload" not in headless.parse_errors(AUTOLOAD, set())[0]


def test_validate_scripts_uses_engine_output(tmp_path, monkeypatch):
    (tmp_path / "project.godot").write_text('[autoload]\n\nGame="*res://game.gd"\n', encoding="utf-8")
    (tmp_path / ".godot").mkdir()
    (tmp_path / ".godot" / "global_script_class_cache.cfg").write_text("list=[]\n", encoding="utf-8")
    outputs = {"res://broken.gd": BROKEN, "res://auto.gd": AUTOLOAD, "res://good.gd": ""}
    monkeypatch.setattr(headless, "run", lambda eng, root, args, timeout=0: {"ok": True, "output": outputs[args[-1]]})
    res = headless.validate_scripts({"exe": "godot"}, tmp_path, ["res://good.gd", "auto.gd", "res://broken.gd"])
    assert res["checked"] == 3 and res["failed"] == 1
    assert res["results"][0]["script"] == "res://broken.gd"


# Captured from Godot 4.7.2 headless, loading shaders through the checker script.
SHADERS = """DUCKY_SHADER res://ok.gdshader
DUCKY_SHADER res://bad.gdshader
--Main Shader--
    1 | shader_type spatial;
E   2-> void fragment() { ALBEDO = vec2(1.0); }
SHADER ERROR: Invalid arguments to operator '=': 'vec3, vec2'.
   at: (null) (:2)
ERROR: Shader compilation failed.
DUCKY_SHADER res://nope.gdshader
ERROR: Cannot load shader: res://nope.gdshader
"""


def test_parse_shader_errors():
    found = headless.parse_shader_errors(SHADERS)
    assert found["res://ok.gdshader"] == []
    assert found["res://bad.gdshader"] == [
        {"kind": "Shader Error", "message": "Invalid arguments to operator '=': 'vec3, vec2'.", "file": "res://bad.gdshader", "line": 2}
    ]
    assert found["res://nope.gdshader"][0]["kind"] == "Load"


def test_shaders_and_scripts_validate_together(tmp_path, monkeypatch):
    (tmp_path / "project.godot").write_text("", encoding="utf-8")
    (tmp_path / ".godot").mkdir()

    def fake_run(eng, root, args, timeout=0):
        return {"ok": True, "output": SHADERS if "--" in args else ""}

    monkeypatch.setattr(headless, "run", fake_run)
    res = headless.validate_scripts({"exe": "g"}, tmp_path, ["res://bad.gdshader", "res://ok.gdshader", "res://a.gd"], tmp_path / "w")
    assert res["checked"] == 3 and res["failed"] == 1
    assert res["results"][0]["script"] == "res://bad.gdshader"
    assert (tmp_path / "w" / "check_shaders.gd").is_file()
    assert not (tmp_path / "check_shaders.gd").exists()


def test_new_class_name_triggers_import_first(tmp_path, monkeypatch):
    (tmp_path / "project.godot").write_text("", encoding="utf-8")
    (tmp_path / ".godot").mkdir()
    cache = tmp_path / ".godot" / "global_script_class_cache.cfg"
    cache.write_text('list=[{\n"base": &"Node",\n"class": &"Player",\n"path": "res://player.gd"\n}]\n', encoding="utf-8")
    (tmp_path / "player.gd").write_text("class_name Player\nextends Node\n", encoding="utf-8")
    assert not headless.stale_class_cache(tmp_path)
    (tmp_path / "wolf.gd").write_text("class_name Wolf\nextends Node\n", encoding="utf-8")
    assert headless.stale_class_cache(tmp_path)

    imported = []
    monkeypatch.setattr(headless, "import_project", lambda eng, root: imported.append(root) or {"ok": True})
    monkeypatch.setattr(headless, "run", lambda eng, root, args, timeout=0: {"ok": True, "output": ""})
    headless.validate_scripts({"exe": "g"}, tmp_path, ["res://wolf.gd"])
    assert imported == [tmp_path]


def test_project_scripts_skips_engine_and_our_addon(tmp_path):
    for rel in ("player.gd", "ui/hud.gd", ".godot/x.gd", "addons/godot_mcp/a.gd", "addons/other/b.gd", "readme.md"):
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")
    assert headless.project_scripts(tmp_path) == ["res://addons/other/b.gd", "res://player.gd", "res://ui/hud.gd"]


def test_export_presets_and_missing_templates(tmp_path, monkeypatch):
    (tmp_path / "export_presets.cfg").write_text(
        '[preset.0]\n\nname="Windows Desktop"\nplatform="Windows Desktop"\nrunnable=true\nexport_path="build/game.exe"\n\n'
        '[preset.0.options]\n\ncustom_template/debug=""\n',
        encoding="utf-8",
    )
    presets = headless.export_presets(tmp_path)
    assert presets == [{"name": "Windows Desktop", "platform": "Windows Desktop", "runnable": "true", "export_path": "build/game.exe"}]
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    eng = {"exe": "godot", "version": {"major": 4, "minor": 7, "patch": 2, "status": "stable"}}
    out = headless.export(eng, tmp_path, "Windows Desktop", "build/game.exe")
    assert not out["ok"] and out["folder"].endswith("4.7.2.stable")
    assert headless.export(eng, tmp_path, "Nope", "x")["presets"] == ["Windows Desktop"]
