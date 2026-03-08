# Debug Assets Package

Placeholder asset package for early frontend integration and terrain iteration.

## Source Of Truth

- `aseprite/**/*.aseprite`: grouped source files
- Timeline tag names are animation IDs
- Each tag maps to a same-named layer

## Wang Tileset (Marching Squares) Placeholder

The debug environment source uses an animated sprite-sheet tag:

- `tilesets.debug.environment.autotile-15`
- Each timeline frame is a full 4x4 tileset sheet (8 phases)

This layout is the Wang tileset convention (also commonly called Blob tileset or
RPG Maker autotile layout).

### Tile Numbering

Case IDs use 4-bit corner masks:

- `NW = 1`
- `NE = 2`
- `SE = 4`
- `SW = 8`
- `caseId = NW*1 + NE*2 + SE*4 + SW*8`

Binary marching-squares row-major reference (case IDs):

```text
0  1  2  3
4  5  6  7
8  9  10 11
12 13 14 15
```

Wang source-sheet slot order in `tileset.aseprite`:

```text
8  6  13 12
5  14 15 11
2  3  7  9
0  4  10 1
```

Expected mapping strategy:

- case `N` -> `tilesets.debug.environment.autotile-15#N`
- animated variants are exported as `tilesets.debug.environment.autotile-15#N@phase`
- source `.aseprite` is authored in Wang slot order; runtime export remaps to binary case IDs (`0..15`)
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
