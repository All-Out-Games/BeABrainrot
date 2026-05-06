# UIK feedback / feature request — custom shaded panel backgrounds

## What we're trying to do

We have a custom shader (`box_panel.aosl`) that draws a styled UI panel:
vertical gradient + procedural halftone dots + bottom accent strip + black
outline + rounded corners + optional diagonal rainbow. The shader needs the
panel's **screen-space rect** as a uniform (`rect_px`) so the gradient/band/
outline align to its edges.

We want UIK to handle layout / scrolling / interaction while each panel's
background is drawn through this shader. Different panels use different
parameters (banner orange, cards yellow/rainbow/purple, etc.).

## What works today

`UI.push_material(...)` before `UIK.begin(...)` *does* propagate to UIK's
panel-background draws — confirmed visually. So at the engine level UIK
respects the active material, which is great.

## What doesn't, and why

UIK is deferred-layout: `panel_begin/end` only record structure; all draws
happen at `UIK.end()`. From CSL we never see a panel's resolved rect during
the begin/end phase, so:

1. **`rect_px` can only be set once** for the whole UIK pass. The gradient/
   band/outline align to whatever rect we guess (usually the modal). Each
   panel can't get its own.
2. **Per-panel parameter swaps don't work** — even if we call
   `mat.set_float4(...)` between `panel_begin` calls, all UIK draws are
   batched at `end`, so they end up using the *last* uniform values.
3. **Pushing the material globally** also tints UIK images: the shader
   writes `lerp(gradient, dotColor, ...)` and ignores `base.rgb`, so any
   `UIK.image_fitted` underneath comes out as the gradient.

## Workaround we landed on (for `shop_v3.csl`)

Use UIK only for layout, then run a **post-end shader pass** that reads the
resolved rect of each panel via the `Interact_Handle` it returned and paints
our shader-backed quad ourselves.

Key pieces:

- Every shaded panel uses `panel_begin_interactive(id, desc)` so we get an
  `Interact_Handle`. The handle resolves to `Interact_Result.rect` — the
  actual screen-space rect (already exists at `generated.csl_engine:550`).
- Every shaded panel sets `desc.show_background = false` so UIK doesn't
  paint its own fill on top.
- `UIK.modal(rect, layer, backdrop_color)` is called with a fully
  transparent backdrop — UIK's built-in backdrop draws at the same layer
  as content and would cover any shader quad placed underneath.
- A manual dim quad is drawn at the default layer (below UIK's content
  layer, e.g. 20). Per-rect shader quads are drawn at the default layer
  too, *after* `UIK.end()`. UIK content (text, images, buttons) renders on
  top of them at layer 20. Sale badges (rotated text) push layer 25 to sit
  above UIK content.

```csl
banner_h := UIK.panel_begin_interactive("banner", banner_desc);
// children
UIK.panel_end();
// ... more panels ...
UIK.end();

// post-end shader pass
banner_rect := UIK.resolve(banner_h).rect;
push_box_panel_material_with_rect(banner_rect, banner_box);
UI.quad(banner_rect, white_sprite, {1,1,1,1});
UI.pop_material();
```

This works, but it's a fair amount of bookkeeping (a handle and a
post-end resolve for every shaded panel) and forces us to suppress UIK's
own background to avoid double-painting.

## What would clean this up — minimal API change

Add a `material: Material` field to `UIK.Panel_Desc`. When UIK draws a
panel's background:

- If `desc.material == null`: existing behaviour (atlas sprite + tint).
- If `desc.material != null`: push the material, automatically set a
  small set of well-known uniforms from the resolved rect, draw the bg
  quad with `core_globals.white_sprite` as albedo, pop the material.

Suggested auto-set uniforms (only set if the shader declares them):

| Uniform | Value | Notes |
|---------|-------|-------|
| `rect_px` | `v4{minX, minY, maxX, maxY}` | Already in screen pixels |
| `corner_radius_px` | `desc.corner_radius` | If we add one |
| `outline_px` | `desc.outline_thickness` | If we add one |

For most users the corner/outline are part of the panel style anyway, so
just setting `rect_px` would already be enough — everything else stays a
shader-only concern that the user configures once on the material itself.

This single field would replace all the workaround above:

```csl
banner_desc := UIK.layout_row();
banner_desc.material = banner_orange_mat; // <-- the only new bit
UIK.panel_begin(banner_desc);
... children ...
UIK.panel_end();
```

No handles, no post-end pass, no `show_background = false` dance, no
fighting UIK's modal backdrop. UIK images and buttons keep their normal
rendering because the material is only pushed during the panel's bg draw,
not during child draws.

## Optional follow-up — exposing `Interact_Result.rect` officially

Decoration overlays (rotated sale stickers, glow effects, animated borders
that shouldn't replace the bg) still need the rect post-end. The handle
already carries it; just making it part of the documented public API
(today it's only visible via the offset annotation in `generated.csl_engine`)
would make this pattern discoverable. Right now the official UIK skill docs
don't mention `result.rect`.

## TL;DR

1. **Best**: `Panel_Desc.material` with auto-set `rect_px`. One field, one
   line of user code per panel, no handle plumbing, no UIK-internal-bg
   conflict. Solves backgrounds cleanly.
2. **Also nice**: officially document `Interact_Result.rect` for
   post-`UIK.end` decoration overlays.

We'll keep using the post-end-pass workaround until either lands. Happy to
test a prototype branch.
