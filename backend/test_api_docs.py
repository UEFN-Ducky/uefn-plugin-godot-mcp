from __future__ import annotations

from backend import api_docs


def test_vendored_reference_lookup():
    out = api_docs.lookup("CharacterBody3D", "move_and_slide")
    assert out["ok"] and out["version"] == "4.7.2"
    assert out["inherits"][:2] == ["PhysicsBody3D", "CollisionObject3D"]
    method = out["methods"][0]
    assert method["signature"] == "move_and_slide() -> bool"
    assert "velocity" in method["description"]


def test_lookup_is_case_insensitive_and_suggests():
    assert api_docs.lookup("node")["class"] == "Node"
    miss = api_docs.lookup("CharacterBody")
    assert not miss["ok"] and "CharacterBody3D" in miss["did_you_mean"]


def test_member_filter_covers_signals_and_properties():
    out = api_docs.lookup("Area3D", "body_entered")
    assert out["signals"][0]["signature"].startswith("body_entered(body: Node3D")
    out = api_docs.lookup("Node3D", "position")
    assert any(m["name"] == "position" and m["type"] == "Vector3" for m in out["members"])


def test_search_ranks_exact_first():
    res = api_docs.search("add_child")
    assert res["results"][0] == "Node.add_child"
    assert api_docs.search("Sprite2D")["results"][0] == "Sprite2D"
