---
description: "Godot shading language: .gdshader spatial and canvas_item shaders, uniforms, ShaderMaterial, setting parameters from code"
metadata:
  label: "Shaders"
---

# Shaders (`.gdshader`)

Write the file with `create_script` / file tools (any text path ending `.gdshader`),
make a `ShaderMaterial` that points at it, assign it to a mesh's `material_override`
or a CanvasItem's `material`.

## Spatial (3D) — dissolve

```glsl
shader_type spatial;

uniform vec4 albedo : source_color = vec4(1.0);
uniform sampler2D noise_tex : hint_default_white;
uniform float dissolve : hint_range(0.0, 1.0) = 0.0;
uniform vec4 edge_color : source_color = vec4(1.0, 0.5, 0.1, 1.0);

void fragment() {
	float n = texture(noise_tex, UV).r;
	if (n < dissolve) {
		discard;
	}
	ALBEDO = albedo.rgb;
	EMISSION = edge_color.rgb * step(n, dissolve + 0.05) * 4.0;
}
```

## canvas_item (2D) — hit flash

```glsl
shader_type canvas_item;

uniform float flash : hint_range(0.0, 1.0) = 0.0;

void fragment() {
	vec4 tex = texture(TEXTURE, UV);
	COLOR = vec4(mix(tex.rgb, vec3(1.0), flash), tex.a);
}
```

## Drive it from GDScript

```gdscript
extends Sprite2D

func hit() -> void:
	var mat := material as ShaderMaterial
	mat.set_shader_parameter("flash", 1.0)
	create_tween().tween_method(func(v: float) -> void: mat.set_shader_parameter("flash", v), 1.0, 0.0, 0.2)
```

- Built-ins: spatial `ALBEDO ROUGHNESS METALLIC NORMAL_MAP EMISSION ALPHA VERTEX`;
  canvas_item `COLOR TEXTURE UV`; time is `TIME`.
- Hints: `source_color` for colours, `hint_range(a, b)`, `hint_normal`, `filter_nearest` for pixel art.
- Live tweak: `set_runtime_shader_parameter` while the game runs.
- Check after every write: `godot_validate_script(scripts="res://fx/dissolve.gdshader")`
  compiles it headless and returns `Shader Error` rows with line numbers.
