---
name: legacy-ui
description: Reference for the legacy immediate-mode UI API in CSL (UI.text / UI.quad / UI.button / Rect). Read this before writing any legacy UI. For declarative flexbox UI use UIK instead.
---

# Legacy UI (CSL) Reference

Immediate-mode rendering for screen-space and world-space interfaces. This is the
`UI.*` API (a direct CSL port of the C# `UI` system). For declarative flexbox
layouts (panels, cards, modals) prefer **UIK** — reach for legacy UI when you need
text-sized backgrounds, manual layering, world-space draws, or pixel-precise control.

## Core principles

1. **Y grows upward** — `(0, 0)` is the bottom-left of the screen. A positive Y
   offset moves UP.
2. **Start from screen rects** — derive everything from `UI.get_screen_rect()`
   (full, centered) or `UI.get_safe_screen_rect()` (respects notches; use for
   edges/corners). Never build a `Rect{}` from raw numbers for screen UI.
3. **Push/pop with `defer`** — every `push_*` needs a matching `pop_*`; use
   `defer` so it always runs:
   ```csl
   UI.push_layer(80);
   defer UI.pop_layer();
   ```
4. **Mobile-first** — no hover-dependent UX; size for touch.
5. **ASCII only** — no emoji. The UI font also lacks the em-dash `—` (it renders
   as a blank gap); use `-` or `,`.
6. **UI procs are plain procs** — take the data they draw as parameters; don't
   read globals.

## Where to draw

Player-interactable UI **must** be drawn in `ao_update` or `ao_late_update`
(prefer late). Gate on `is_local_or_server()` (UI only), and wrap legacy draws in
a screen draw context:

```csl
ao_late_update :: method(dt: float) {
    if is_local_or_server() {
        draw_my_hud(this);
    }
}

draw_my_hud :: proc(player: Player) {
    UI.push_screen_draw_context();
    defer UI.pop_draw_context();

    rect := UI.get_safe_screen_rect().bottom_right_rect().grow(40, 100, 40, 100).offset(-50, 50);
    bs := UI.default_button_settings();
    ts := get_text_settings(24);
    if UI.button(rect, bs, ts, "Action").clicked {
        // do thing
    }
}
```

## Basic drawing

### Quads / images / lines

```csl
// Textured quad (default white tint)
rect := UI.get_screen_rect().center_rect().grow(100); // 200x200 at center
UI.quad(rect, my_texture);

// With an RGBA tint (0..1)
UI.quad(rect, my_texture, v4{1, 0, 0, 0.5}); // red, 50% alpha

// Solid color fill via the white sprite
UI.quad(rect, core_globals.white_sprite, v4{0, 0, 0, 0.75});

// Lines / debug shapes
UI.line(a, b, thickness, core_globals.white_sprite, v4{1,1,1,1});
UI.wire_box(lo, hi, thickness, v4{0,1,0,1});
UI.wire_circle(center, radius, thickness);
```

### Text

```csl
rect := UI.get_screen_rect().center_rect().grow(200, 300, 50, 300);
ts := get_text_settings(48);

// Draw (does not return anything)
UI.text(rect, ts, "Hello, World!");

// Format args go in a trailing list — like format_string
UI.text(rect, ts, "HP: %0%%", {hp});

// text_sync draws AND returns the actual rendered rect (for backgrounds/layout)
text_rect := UI.text_sync(rect, ts, "Dynamic");

// measure_text returns the rect WITHOUT drawing (size a background first, then draw)
text_rect := UI.measure_text(rect, ts, "Dynamic");
```

### Text_Settings

Start from `UI.default_text_settings()` (Barlow-Black, size 32, centered, black
outline) and override fields:

```csl
ts := UI.default_text_settings();
ts.size              = 48;
ts.color             = v4{1, 1, 1, 1};
ts.halign            = .CENTER;    // .LEFT .CENTER .RIGHT
ts.valign            = .CENTER;    // .TOP  .CENTER .BOTTOM
ts.do_outline        = true;
ts.outline_thickness = 3.0;
ts.outline_color     = v4{0, 0, 0, 1};
ts.word_wrap         = false;      // UIK doesn't wrap for you; legacy does if true
ts.do_autofit        = true;       // shrink to fit the rect
ts.autofit_min_size  = 24;
ts.autofit_max_size  = 70;
```

Notable fields: `font`, `size`, `color`, `halign`, `valign`, `word_wrap`,
`overflow_wrap`, `offset`, `do_drop_shadow`, `drop_shadow_offset`,
`drop_shadow_color`, `do_outline`, `outline_thickness`, `outline_color`,
`weight`, `slant`, `do_autofit`, `autofit_min_size`, `autofit_max_size`.

### Text-sized background (common pattern)

```csl
text_rect := UI.measure_text(box, ts, msg);
UI.quad(text_rect.grow(10), core_globals.white_sprite, v4{0, 0, 0, 0.5}); // strip
UI.text(box, ts, msg);
```

## Rect functions

All values are **1080p-reference pixels** — every rect method auto-multiplies by
the UI scale factor (`screen_height / 1080`).

```csl
// Point rects (0x0 at an anchor)
r.center_rect()
r.top_left_rect()  r.top_center_rect()  r.top_right_rect()
r.left_center_rect()                    r.right_center_rect()
r.bottom_left_rect() r.bottom_center_rect() r.bottom_right_rect()

// Edge rects (one dimension full, one zero — growing these gives rectangles)
r.top_rect()  r.right_rect()  r.bottom_rect()  r.left_rect()

// Grow / inset. ORDER IS (top, right, bottom, left) — CSS-clockwise.
r.grow(t, r, b, l)     r.grow(all)
r.inset(t, r, b, l)    r.inset(all)
r.grow_top(px) r.grow_right(px) r.grow_bottom(px) r.grow_left(px)
r.inset_top(px) ...

// Cut — returns the slice, you re-assign the remainder (see pattern below)
r.cut_top(px)  r.cut_right(px)  r.cut_bottom(px)  r.cut_left(px)

// Move / scale
r.offset(x, y)         // move, keep size
r.scale(x, y)          // multiply dimensions
r.slide(x, y)          // move by a fraction of own size
r.fit_aspect(aspect, .AUTO|.KEEP_WIDTH|.KEEP_HEIGHT|.KEEP_BIGGER)
r.subrect(x0, y0, x1, y1)  // percentage sub-rect (health bars etc.)

// Queries (these are methods — call them)
r.width()  r.height()  r.center()  r.top_left()  r.bottom_right()
```

### Auto-scaling vs `_unscaled`

When you feed a **computed pixel value** (e.g. another rect's `width()`, which is
already scaled), use the `_unscaled` variant or you double-scale:

```csl
// WRONG — width() is already scaled, offset() scales again
row = row.offset(0, -row.height());
// RIGHT
row = row.offset_unscaled(0, -row.height());
```

Available: `offset_unscaled`, `grow_unscaled`, `inset_unscaled`, `cut_*_unscaled`,
and the per-side variants (`grow_top_unscaled`, etc.).

### Cutting pattern (sequential layouts, no overlap)

```csl
r := UI.get_safe_screen_rect();
header  := r.cut_top(60);     // takes 60 off the top; r shrinks
footer  := r.cut_bottom(40);
sidebar := r.cut_left(200);
content := r;                 // whatever remains
```

### Grid layout

```csl
grid := UI.Grid_Layout.make(rect, 4, 6, .ELEMENT_COUNT, padding = 8);
for i: 0..items.count - 1 {
    UI.push_id("%", {i});
    defer UI.pop_id();
    slot := grid.next();
    // draw item in slot
}
```

## Buttons

```csl
bs := UI.default_button_settings();
bs.sprite = get_asset(Texture_Asset, "$AO/new/modal/buttons_2/button_2.png"); // green
ts := get_text_settings(24);

res := UI.button(rect, bs, ts, "Click Me");
if res.clicked {
    // pressed and released
}
```

`Interact_Result` fields: `clicked`, `pressed`, `just_pressed`, `released`,
`active`, `hovering`, `double_clicked`, `active_t` / `active_t_eased` (0..1 press
animation), `rect`. Push a unique id per repeated button (`UI.push_id`).

Button sprite paths: `$AO/new/modal/buttons_2/button_1.png` orange, `_2` green,
`_3` red, `_5` blue, `_7` pink, `_8` grey, `_9` white.

## State management (all paired with `defer`)

```csl
UI.push_layer(100);              defer UI.pop_layer();   // higher = on top
UI.push_layer_relative(10);      defer UI.pop_layer();
UI.push_z(pos.y);                defer UI.pop_z();       // world-space depth sort
UI.push_scale_factor(1.5);       defer UI.pop_scale_factor();
UI.push_color_multiplier(v4{1,1,1,0.5}); defer UI.pop_color_multiplier(); // fade a whole subtree
UI.push_material(mat);           defer UI.pop_material(); // custom shader (e.g. mutation glow)
UI.push_scissor(rect);           defer UI.pop_scissor();  // hard clip
UI.push_id("%", {i});            defer UI.pop_id();        // disambiguate repeats
```

Alpha-shape masking:

```csl
mask := UI.build_mask_begin(rect);
// draw the mask shape (e.g. a bubble sprite)
UI.build_mask_end();
UI.use_mask_begin(mask);
// draw content — clipped to the mask's alpha
UI.use_mask_end();
```

## World-space UI

For health bars, name tags, held items — **use world units (meters)**, anchored to
an entity so it interpolates smoothly:

```csl
UI.push_world_draw_context();
defer UI.pop_draw_context();
UI.begin_world_space_ui(entity);  // adds the entity's interpolation offset
defer UI.end_world_space_ui();
UI.push_z(entity.world_position.y); // sort against the world
defer UI.pop_z();

bar_pos := entity.world_position + v2{0, 1.5}; // 1.5m above
bar := Rect{bar_pos - v2{0.5, 0.1}, bar_pos + v2{0.5, 0.1}};
UI.quad(bar, core_globals.white_sprite, v4{0, 0, 0, 0.8});
fill := bar.inset(0.02).subrect(0, 0, health_pct, 1);
UI.quad(fill, core_globals.white_sprite, v4{0, 1, 0, 1});
```

## Scroll views

```csl
sv := UI.push_scroll_view(rect, "my_scroll", Scroll_View_Settings{vertical = true});
defer UI.pop_scroll_view();
content := sv.content_rect;
for i: 0..items.count - 1 {
    row := content.cut_top(40);
    UI.text(row, ts, items[i]);
}
```

## Common text-settings helper

```csl
get_text_settings :: proc(size: float, color: v4 = v4{1, 1, 1, 1}) -> Text_Settings {
    ts := UI.default_text_settings();
    ts.size              = size;
    ts.color             = color;
    ts.halign            = .CENTER;
    ts.valign            = .CENTER;
    ts.do_outline        = true;
    ts.outline_thickness = 3.0;
    return ts;
}
```

## Gotchas

- **`grow`/`inset` arg order is `(top, right, bottom, left)`** (CSS-clockwise), not
  (left, top, right, bottom).
- **`width()` / `height()` / `center()` are methods** — call them with `()`.
- **Edge rects** (`left_rect()`, `top_rect()`...) are line-shaped; growing them
  gives a rectangle. Use a point rect (`left_center_rect()`) to grow into a square.
- **Layer ordering** is by layer value, not draw order. To put a strip behind text,
  draw the text at layer N and the strip at N-1 (or just `measure_text` then draw
  strip-before-text at the same layer).
- **No em-dash** in any string — the font renders it as a blank gap.
- Constants in your code are 1080p-reference; rect methods scale them. Only reach
  for `_unscaled` when passing an already-scaled computed value back in.
```
