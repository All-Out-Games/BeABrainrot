# Be a Brainrot

A multiplayer collection and progression game for [All Out](https://allout.game/). Venture into an NPC-guarded area, steal brainrots, escape the chase, and bring your collection home. Place brainrots on pedestals to earn cash, upgrade your movement and collection, unlock space, and rebirth for further progression.

The GitHub repository is `BeABrainrot`; existing local checkouts may be named `steal-from-brainrots`. Both names refer to this project.

## Script architecture

| Start here | Responsibility |
| --- | --- |
| [scripts/main.csl](scripts/main.csl) | Imports, startup registration, `Player` state, cash helpers, saving, and player UI. |
| [scripts/game_manager.csl](scripts/game_manager.csl), [npc_chaser.csl](scripts/npc_chaser.csl) | The guarded area, boundary interactions, chase behavior, and returning from a steal. |
| [scripts/brainrot_config.csl](scripts/brainrot_config.csl), [brainrot_inventory.csl](scripts/brainrot_inventory.csl), [live_entity.csl](scripts/live_entity.csl) | Collectible definitions, inventory integration, and brainrots represented in the world. |
| [scripts/room.csl](scripts/room.csl) | Player rooms, pedestals, placed brainrots, and generated cash. |
| [scripts/floor_manager.csl](scripts/floor_manager.csl), [floor_grid.csl](scripts/floor_grid.csl), [floor_renderer.csl](scripts/floor_renderer.csl), [floor_switcher.csl](scripts/floor_switcher.csl) | Multi-floor layout, navigation, and presentation. |
| [scripts/effects/](scripts/effects/) | Carrying, chasing, capture, knockback, and movement sequences. |
| [scripts/rebirth.csl](scripts/rebirth.csl), [speed_upgrades.csl](scripts/speed_upgrades.csl), [offline_earnings.csl](scripts/offline_earnings.csl) | Long-term progression and earnings between sessions. |
| [scripts/tutorial/](scripts/tutorial/), [events/](scripts/events/) | Guided first steps and timed/event-specific behavior. |

The main loop is **steal → escape → place → earn → upgrade**. Effects represent temporary actions such as carrying and being chased; the player, inventory, room, and pedestal systems hold the longer-lived collection and progression state.

## How CSL works here

CSL is All Out's statically typed scripting language. [ao.project](ao.project) enables it with `"csl": true`; the All Out editor compiles the source for its engine.

- `main.csl` imports `core:ao` plus the `effects`, `tutorial`, and `events` folders. Its `ao_before_scene_load` registers collectible definitions and rebirth levels and enables automatic inventory saving.
- `Player` extends `Player_Base`; components and interactables implement the NPC area, rooms, and pedestals. Fields marked `@ao_serialize` connect those behaviors to scene entities and settings.
- Startup and frame callbacks advance the game. Temporary effects encapsulate action lifetimes so carrying, capture, and escape logic can start and finish together.
- All Out supplies client prediction and authoritative server reconciliation. World changes belong in shared gameplay; player-specific collection and progression stay with their owner. Inventory and save APIs provide persistence beyond an individual match.

[scene/](scene/) contains the authored world, and [res/](res/) contains project assets. Engine API references live in `scripts/.ao_core/` and `api_references/`. [scripts/docs/BRAINROT_SCALING.md](scripts/docs/BRAINROT_SCALING.md) provides more detail on collectible scaling.

## Open and remix

1. Set up the [Windows All Out editor](https://docs.allout.game/getting-started/first-game).
2. Clone the project:

   ```sh
   git clone https://github.com/All-Out-Games/BeABrainrot.git
   ```

3. Select the cloned folder containing `ao.project` with **Open project**. Wait for script compilation and asset preparation, then press **Play**. Use multiple clients to check that chases, inventories, rooms, and pedestal earnings stay with the correct players.
4. Before publishing a remix, create your own game and associate the working copy with its identity. Review game-specific product IDs, progression values, and event configuration for your version; the checked-in project IDs identify the original games.

Requires the All Out editor/runtime and referenced platform assets. Saving scripts triggers compilation; restart play mode after scene or startup-registration changes. See [CSL syntax](https://docs.allout.game/scripting/syntax), [networking](https://docs.allout.game/scripting/networking-fundamentals), and [playtesting](https://docs.allout.game/getting-started/playtesting-your-game).

## License

The code, documentation, and original assets contributed by All Out Games are available under the [MIT License](LICENSE). You may copy, modify, remix, distribute, and use them in commercial games, including games published on All Out. Keep the copyright and license notice with copies or substantial portions.

Separately licensed third-party material retains its own terms. References to platform-provided assets, such as `$AO/...`, do not transfer ownership of those assets or license the All Out engine and services.
