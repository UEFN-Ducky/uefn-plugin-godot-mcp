from __future__ import annotations

from backend import projects
from backend.constants import ADDON_CFG

BASE = """; Engine configuration file.
config_version=5

[application]

config/name="My Game"
config/features=PackedStringArray("4.7")

[rendering]

renderer/rendering_method="mobile"
"""


def _project(tmp_path, text=BASE):
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "project.godot").write_text(text, encoding="utf-8", newline="\n")
    return tmp_path


def test_project_root_from_file_parent_and_child(tmp_path):
    root = _project(tmp_path / "game")
    (root / "scenes").mkdir()
    assert projects.project_root(root / "scenes") == root
    assert projects.project_root(root / "project.godot") == root
    assert projects.project_root(tmp_path) == root
    assert projects.project_root(tmp_path / "nope") is None
    assert projects.project_name(root) == "My Game"


def test_enabled_plugins_round_trip():
    text = BASE + '\n[editor_plugins]\n\nenabled=PackedStringArray("res://addons/a/plugin.cfg", "res://addons/b/plugin.cfg")\n'
    assert projects.enabled_plugins(text) == ["res://addons/a/plugin.cfg", "res://addons/b/plugin.cfg"]
    out = projects.set_enabled_plugins(text, ["res://addons/a/plugin.cfg"])
    assert projects.enabled_plugins(out) == ["res://addons/a/plugin.cfg"]
    assert out.count("[editor_plugins]") == 1 and "[rendering]" in out


def test_install_then_uninstall_restores_bytes(tmp_path):
    root = _project(tmp_path)
    first = projects.install_addon(root)
    assert first["ok"] and first["copied"] and first["enabled_now"]
    assert (root / "addons" / "godot_mcp" / "plugin.cfg").is_file()
    assert projects.enabled_plugins((root / "project.godot").read_text()) == [ADDON_CFG]
    assert projects.addon_status(root) == {"installed": True, "enabled": True, "current": True}
    again = projects.install_addon(root)
    assert not again["copied"] and not again["enabled_now"]
    # The addon registers its runtime probe in the editor; uninstall removes that too.
    text = (root / "project.godot").read_text()
    (root / "project.godot").write_text(
        text + '\n[autoload]\n\nMCPRuntimeProbe="*res://addons/godot_mcp/runtime/mcp_runtime_probe.gd"\n', encoding="utf-8"
    )
    projects.uninstall_addon(root)
    assert (root / "project.godot").read_text() == BASE
    assert not (root / "addons" / "godot_mcp").exists()


def test_install_keeps_other_plugins_and_autoloads(tmp_path):
    text = BASE + '\n[autoload]\n\nGame="*res://game.gd"\n\n[editor_plugins]\n\nenabled=PackedStringArray("res://addons/x/plugin.cfg")\n'
    root = _project(tmp_path, text)
    projects.install_addon(root)
    assert projects.enabled_plugins((root / "project.godot").read_text()) == ["res://addons/x/plugin.cfg", ADDON_CFG]
    projects.uninstall_addon(root)
    assert (root / "project.godot").read_text() == text


def test_stale_addon_is_replaced(tmp_path):
    root = _project(tmp_path)
    projects.install_addon(root)
    (root / "addons" / "godot_mcp" / projects.STAMP).write_text("old", encoding="utf-8")
    assert not projects.addon_status(root)["current"]
    assert projects.install_addon(root)["copied"]


def test_no_project(tmp_path):
    assert not projects.install_addon(tmp_path)["ok"]
