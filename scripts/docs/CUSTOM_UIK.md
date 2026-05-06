# Custom UIK Shading — Notes for Future Me

## What we're doing

We want UIK to handle layout (sizing, alignment, scrolling, click handling)
while our `box_panel.aosl` shader paints each panel's background — gradient
fill, halftone dots, pink/red bottom band, black outline, rounded corners,
optional diagonal rainbow.

The naive approach (`UI.push_material(...)` before `UIK.begin`) **does** make
UIK render through the shader, but the same `rect_px` uniform applies to
every panel, so the gradient/band/outline only line up with one global rect
(usually the modal). It also tints UIK images because the shader's output
ignores the bound texture's RGB.

## The fundamental problem

UIK is **deferred-layout**: `panel_begin/end` only record structure. All
draws happen at `UIK.end()`. While we're describing the layout, we don't
know any panel's resolved rect — so we can't pre-set `rect_px` per panel,
and we can't interleave material pushes between panels' draws.

## The trick: post-end shader pass

Use UIK to lay things out, but read the resolved rects **after** `UIK.end()`
and paint our shader-backed quads from CSL.

### How to get a panel's resolved rect

`UIK.panel_begin_interactive(id, desc)` returns an `Interact_Handle`. The
struct it resolves into (`UIK.resolve(handle)`) has a `rect: Rect` field
(see `generated.csl_engine:550`). That rect is the post-layout screen-space
rectangle of the panel.

```csl
banner_h := UIK.panel_begin_interactive("banner", banner_desc);
... children ...
UIK.panel_end();
UIK.end();

banner_rect := UIK.resolve(banner_h).rect;
```

> First frame after the modal opens, the rect can be uninitialised. Check
> `rect.max.x > rect.min.x` before using it.

### Suppress UIK's own background fill

Without this, UIK paints its own panel background at the same rect, which
sits under our shader quad — fine — but adds visual noise. Set
`desc.show_background = false` on every panel we plan to shade ourselves.

```csl
banner_desc := UIK.layout_row();
banner_desc.show_background = false;   // we'll paint it
```

For the shell, instead of `panel_modal(.BLACK)` (which paints a dark fill
over our backdrop), use a plain `layout_column` with `show_background = false`.

### Transparent UIK modal backdrop

`UIK.modal(rect, layer)` draws a 0.5-alpha black backdrop at the same layer
as content (so it'd cover any shader quads we placed below). Use the 4-arg
overload with `v4{0,0,0,0}` and paint our own dim quad before `UIK.begin`.

```csl
UI.push_screen_draw_context();
UI.quad(UI.get_screen_rect(), core_globals.white_sprite, v4{0, 0, 0, 0.5});
UI.pop_draw_context();

UIK.begin(UIK.modal(UIK.rect_window(), 20, v4{0, 0, 0, 0}));
```

## Layer ordering

UIK's content layer is whatever you pass to `UIK.modal(..., layer)` — we use
**20**. Within the same layer, draws go in submission order. Layers are
sorted at flush time (higher = on top).

Final stack (back → front):

| Layer | Content |
|-------|---------|
| default (0) | World tiles |
| default | **Manual dim quad** (faded black) |
| default | **Modal bg shader** (whole `UIK.rect_window()` dark blue) |
| default | **Per-panel shader quads** (banner orange, cards yellow/rainbow/purple) |
| default | **Ray bursts** behind icons |
| 20 | **UIK content** — text, images, buttons |
| 25 | **Rotated sale badges** (`+25 Free`, `+100 Free`) — sit on top |

So the per-rect shader sits BELOW UIK content because UIK runs at layer 20
and we draw at default (= layer 0). Badges go ABOVE because we explicitly
push layer 25 around them.

## Anatomy of `draw_shop_v3`

```
1. Dim full-screen quad (default layer, push_screen_draw_context)
2. UIK.begin(UIK.modal(rect_window, 20, transparent backdrop))
3. shell  = layout_column with show_background = false
4. UIK.title_area("Store")
5. banner = layout_row, show_background = false, get banner_h via panel_begin_interactive
   - icon panel, text column, price button (UIK widgets)
6. cards_row with show_background = false
   - 3 cards via draw_shop_v3_card → each is a panel_begin_interactive returning a handle
     with name text, image, currency widget
7. UIK.end()
8. Post-end shader pass at default layer:
   - shop3_push_box(modal_rect, shop3_box_modal_bg())  -- whole modal blue bg
   - For each handle: resolve → rect → shop3_push_box(rect, preset)
   - Draw rays behind each card (fit_aspect + rotate_about_point)
9. push_layer(25) → draw rotated sale badges → pop_layer
10. pop_draw_context
11. Resolve interaction handles (close button, buy clicks)
```

## Things that DON'T work / pitfalls

- **Pushing the material globally** before `UIK.begin`: it does apply to
  UIK draws, but every panel uses the same `rect_px` (so gradient/band
  align to one rect), and UIK images render as the shader gradient instead
  of their actual texture (the shader writes `lerp(grad, dot, ...)` and
  ignores `base.rgb`).
- **`UI.push_layer(-1)` for shader quads with UIK's modal backdrop**: UIK
  backdrop is at the same layer as content (e.g. 20), so anything below
  that gets covered. That's why we kill UIK's backdrop and draw our own.
- **Negative layers very far back** (e.g. `-200`): can fall *behind* world
  rendering depending on the engine, leaving us with no visible dim. Stick
  near the default layer 0 for screen-space dim.
- **Constructing rects with manual offsets in unscaled space** when other
  values come from `rect.height()` etc.: leads to double scaling. Use
  `*_unscaled` variants when the value is already in screen pixels, scaled
  variants when it's a 1080p reference number.
- **Computing the `rect_px` uniform from a rect that doesn't match where
  the shader ends up drawing**: gradient and bottom band misalign with
  the panel edges. Always pass the same rect you're drawing the quad at.

## When to use which approach

- **`shop_v2.csl`** (raw UI, fully manual): use when you need pixel-perfect
  control over every element and don't need scrolling / complex layout.
- **`shop_v3.csl`** (UIK + post-end shader pass): use when you want UIK's
  layout/scrolling/widgets but still want the custom shader background per
  panel. Trade-off: a touch more bookkeeping (handles, rect resolves), and
  rotation/effects on text need a separate `push_layer` pass after UIK.

## What would simplify all of this

Engine-side: a `material: Material` field on `UIK.Panel_Desc`. UIK would
push it, set `rect_px` (and a few well-known uniforms like `corner_radius`)
from the resolved rect, draw the bg quad, pop. One field, no manual handle
plumbing. Until that ships, the post-end pass approach above is the way.
