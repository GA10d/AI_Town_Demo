# AI Town Python

Python/Pygame rewrite of the current Cocos prototype.

It keeps the existing Cocos/Tiled assets in `../assets` and implements:

- Main menu with Start, Continue, LLM Test, Settings, and Quit.
- Tiled `.tmx` + external `.tsx` tileset parsing.
- Rendering of `assets/tilemap/map_test.tmx`.
- Local JSON settings/save files.
- LLM health check and chat calls against the existing Node backend.

## Run

```powershell
conda activate AI_Town
python python_town/main.py
```

The LLM test panel uses the existing backend URL setting, defaulting to
`http://127.0.0.1:8787`. Start it with:

```powershell
npm run start:llm
```

## Controls

- Up/Down or W/S: move menu selection.
- Enter/Space: activate selected menu item.
- Esc: back/close panel, or return from the map to the menu.
- WASD in the map scene: move the test character; the camera follows.
- J in the map scene: answer/hang up the phone animation.
- Q/E, +/- or PageUp/PageDown in the map scene: zoom the camera.
- Home or 0 in the map scene: reset the camera on the character.

## Code Layout

- `main.py`: thin executable entry point.
- `app.py`: pygame lifecycle and scene switching.
- `menu.py`: main menu, settings, and LLM test UI.
- `map_scene.py`: test scene orchestration, movement, collision, and drawing order.
- `tilemap.py`: TMX/TSX parsing and tile layer data.
- `player.py` + `animation.py`: character state machine and sprite frames.
- `furniture.py`: furniture catalog, placements, images, and CSV parsing.
- `camera.py`, `input.py`, `graphics.py`, `storage.py`, `llm.py`: focused support systems.

## Furniture Data

Furniture is configured with two CSV files:

- `python_town/data/furniture_catalog.csv`: `id,description`
- `python_town/data/furniture_placements.csv`: `id,cell,size,access_tiles,blocks_movement`

Put furniture PNGs in `assets/resources/furniture/<id>.png`. The renderer also checks
`art/furniture/<id>.png` for local raw art. `cell` is the bottom-left tile occupied by
the furniture, using Tiled grid coordinates. `size` is tile units such as `1x1` or
`2x1`. `access_tiles` is a manually chosen list of destination cells, for example
`"(1,1);(2,1)"`. `blocks_movement` is `true` when every tile covered by the
furniture should be blocked for movement/pathfinding, or `false` when characters
can stand inside those cells.

To add new furniture art, put PNGs in `assets/resources/furniture` and run:

```powershell
python python_town\tools\sync_furniture_data.py
```

or double-click `sync_furniture_data.bat` from the repository root. The sync only
adds missing ids; it does not overwrite descriptions, positions, sizes, or access
tiles that already exist in the CSV files.

## Tile Slicing

Slice a PNG into numbered tiles:

```powershell
python python_town\tools\slice_png_tiles.py path\to\sheet.png path\to\output --tile-size 32
```

Fully transparent tiles are skipped by default. A configurable notebook is available at
`python_town/notebooks/slice_png_tiles.ipynb`.
