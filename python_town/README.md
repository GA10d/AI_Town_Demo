# AI Town Python

Python/Pygame rewrite of the current Cocos prototype.

It keeps the existing Cocos/Tiled assets in `../assets` and implements:

- Main menu with Start, Continue, LLM Test, Settings, and Quit.
- Tiled `.tmx` + external `.tsx` tileset parsing.
- Rendering of `assets/tilemap/map_test.tmx`.
- Simple controllable player marker on the map scene.
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
- Arrow keys or WASD in the map scene: move the player marker.
