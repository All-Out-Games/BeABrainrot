# Brainrot Level Scaling

Every brainrot — regardless of rarity — uses the same two multiplicative
curves for GPS (gold-per-second) and upgrade price as it levels up. Only
the **base values** (`base_gps`, `base_price` in `brainrot_config.csl`)
change between rarities.

## The Constants

Defined once in `scripts/live_entity.csl`:

```csl
PRICE_PER_LEVEL_MULT :: 1.5;   // upgrade cost grows ×1.5 per level
GPS_PER_LEVEL_MULT   :: 1.25;  // GPS grows ×1.25 per level
```

Used by both `LivingEntity` (placed brainrots) and `Brainrot_Item`
(inventory items).

## The Formulas

For a brainrot at level `lvl` (lvl starts at 1):

```
gps(lvl)   = base_gps   * 1.25 ^ (lvl - 1)
price(lvl) = base_price * 1.5  ^ (lvl - 1)   // cost to upgrade lvl → lvl+1
```

Sell price (inventory): `get_brainrot_item_sell_price = gps(lvl) * 10`.

## Why ×1.25 / ×1.5 (the "feel" of the curve)

Price grows faster than GPS, so the **payback time** at each level is
multiplied by `1.5 / 1.25 = 1.2` — every upgrade takes ~20% longer to
break even than the previous one. That's what makes higher levels feel
progressively harder without ever being unreachable.

## Example: Reverse-Engineered From a Reference Game

The same curve was confirmed against another game's brainrot data.

### Very-rare tier (data starts at lvl 1)

| Lvl | GPS       | Upgrade price |
|-----|-----------|---------------|
| 1   | 1.05 B/s  | 105 M         |
| 2   | 1.31 B/s  | 157.5 M       |
| 3   | 1.64 B/s  | 236.24 M      |
| 4   | 2.05 B/s  | 354.37 M      |
| …   | …         | …             |
| 32  | 1.06 T/s  | 30.2 T        |

Ratios: `1.31 / 1.05 = 1.248`, `1.64 / 1.31 = 1.252`, … → **×1.25 GPS**.
`157.5 / 105 = 1.50`, `236.24 / 157.5 = 1.50`, … → **×1.5 price**.

### Common tier (data started at lvl 2 → lvl 1 inferred)

| Lvl | GPS    | Upgrade price |
|-----|--------|---------------|
| 1   | ~12.8/s| ~$19          | *(inferred: 16/1.25, 29/1.5)*
| 2   | 16/s   | $29           |
| 3   | 20/s   | $43           |
| 4   | 25/s   | $65           |
| …   | …      | …             |

Same ×1.25 / ×1.5 curve.

## Per-Rarity Tuning

The only knob that varies by rarity is the **starting price/GPS ratio**
at lvl 1. In the reference data:

| Rarity    | base_gps | base_price | price/gps at lvl 1 |
|-----------|----------|------------|--------------------|
| Common    | ~12.8/s  | ~$19       | 1.51               |
| Very rare | 1.05 B/s | $105 M     | 0.10               |

Higher-rarity brainrots have a *lower* starting price/GPS ratio — they
pay back faster early, which makes rare drops feel rewarding. Tune
`base_price` and `base_gps` per rarity in
`brainrot_config.csl::get_brainrot_configs`; do **not** change the
`1.25` / `1.5` constants unless you want to retune the entire game's
progression curve.

## Where to Look in Code

- Constants: `scripts/live_entity.csl` (top of file)
- Placed-brainrot math: `LivingEntity.get_upgrade_price`,
  `LivingEntity.get_gps` in `scripts/live_entity.csl`
- Inventory math: `get_brainrot_item_gps`,
  `get_brainrot_item_sell_price` in `scripts/brainrot_inventory.csl`
- Per-rarity base values: `get_brainrot_configs` in
  `scripts/brainrot_config.csl`
