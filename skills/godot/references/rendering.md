---
description: "Godot rendering: Forward+/Mobile/Compatibility renderers, WorldEnvironment, lights and shadows, global illumination choices"
metadata:
  label: "Rendering"
---

# Rendering

| Renderer | Pick when |
|----------|-----------|
| Forward+ | Desktop 3D, best features (SDFGI, volumetric fog, SSR) |
| Mobile | Phones / weaker GPUs, simpler 3D |
| Compatibility | Web export, very old GPUs, most 2D games |

Set in `project.godot` `rendering/renderer/rendering_method` (`forward_plus`, `mobile`,
`gl_compatibility`) — change it before building lots of content.

## A good-looking 3D baseline

1. `WorldEnvironment` with an `Environment`: Sky (`ProceduralSkyMaterial`), tonemap
   **AgX** or Filmic, glow on, SSAO on (Forward+).
2. `DirectionalLight3D` (sun) with shadows on; angle ~ -45° pitch.
3. `ReflectionProbe` in interiors; fill with a few `OmniLight3D` / `SpotLight3D`.
4. Global illumination:

| GI | Use |
|----|-----|
| SDFGI | Big open worlds, real time (Forward+ only) |
| VoxelGI | Small/medium rooms, real time, bake the probe data |
| LightmapGI | Static scenes, best quality/perf, bake (needs UV2) |

## 2D

`CanvasModulate` for global tint, `PointLight2D` + `LightOccluder2D` for lights and
shadows, `WorldEnvironment` glow works in 2D too (Forward+/Mobile).

## Check performance

`get_performance_metrics` / `get_runtime_performance_snapshot` (FPS, draw calls,
memory). Reduce draw calls with `MultiMeshInstance3D` for repeated props and mesh LODs
(automatic on import).
