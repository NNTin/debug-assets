# Debug Assets Package

Placeholder asset package for early frontend integration and terrain iteration.

## Source Of Truth

- `aseprite/**/*.aseprite`: grouped source files
- Timeline tag names are animation IDs
- Each tag maps to a same-named layer

## Marching Squares Placeholder

The debug environment source uses an animated sprite-sheet tag:

- `tilesets.debug.environment.autotile-15`
- Each timeline frame is a full 4x4 tileset sheet (8 phases)
- Source sheet slot order is Blob/RPG Maker autotile layout:
  - row 1: `8 6 13 12`
  - row 2: `5 14 15 11`
  - row 3: `2 3 7 9`
  - row 4: `0 4 10 1`

Expected mapping strategy:

- case `N` -> `tilesets.debug.environment.autotile-15#N`
- animated variants are exported as `tilesets.debug.environment.autotile-15#N@phase`
- runtime export still emits binary marching case IDs (`0..15`) regardless of source slot order
- canonical ruleset example: `aseprite/environment/tileset.marching-squares-15.json`

## Outputs

- Phaser runtime files in `apps/frontend/public/assets/debug`
- GIF previews in `previews/` (via `export:all`) showing full sheet animation
- Sliced case frame sequences in `frames/` (via `export:all`)

## Commands

```bash
npm run export:dry
npm run export:public
npm run export:all
```

Legacy binary source order is still available during migration:

```bash
python3 pipeline/export_from_aseprite.py --source-layout binary
```
