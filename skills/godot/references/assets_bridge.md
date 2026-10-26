---
description: "Bring assets into Godot: GLB from Blender, Meshy, Tripo, textures and audio, import settings, collision, and moving work between Godot and UEFN"
metadata:
  label: "Assets bridge"
---

# Assets bridge

Godot imports whatever lands under `res://`: copy the file into the project folder,
then `reimport_resources` (live) or `godot_import` (headless).

| Asset | Format | Notes |
|-------|--------|-------|
| Models | **GLB** (glTF 2.0) | +Y up, meters, materials and animations come along |
| Textures | PNG / WebP / JPG | 2D pixel art: filter Nearest in import settings |
| Audio | OGG (music), WAV (short SFX) | MP3 works too |
| Fonts | TTF / OTF | Use in a Theme |

Blender export rules (scale, collision suffixes, animation clips) live in the
`godot-export` skill pack: `skill_read_subskill("godot-export", "core")`.

## Sources in Ducky

- **Blender** plugin → export GLB into `<project>/assets/`.
- **Meshy / Tripo** plugins → download GLB (`meshy_download` / `tripo_download`) into the project.
- **UEFN** → there is no live link; FBX/GLB exported from UEFN or its source Blender file
  is the hop. Verse and GDScript do not convert into each other.

## After import

- Instance the `.glb` like a scene (`instantiate()` or drag via `create_node` +
  scene instancing), or open it as a new inherited scene to add scripts.
- Collision: in Blender name meshes `-col` / `-convcolonly`, or in Godot add a
  `StaticBody3D` + `CollisionShape3D` (trimesh/convex) under the mesh.
- Animations from a GLB appear in its `AnimationPlayer`; set loop in the import settings.
- Check the result: `get_import_metadata`, `get_resource_dependencies`, a screenshot.
