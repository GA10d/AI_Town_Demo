# AI Town Demo

English | [简体中文](README.zh-CN.md)

AI Town Demo is an experimental project exploring the boundaries of AI-driven narrative. It aims to turn open-ended LLM interaction into a practical, repeatable gameplay pipeline: prompts, structured outputs, CSV-authored world data, local assets, and runtime behaviors are kept explicit so designers and programmers can collaborate without stepping on each other's work.

The implementation is also inspired by *AI2U*, whose first public demo appeared around March 2023. At a time when structured LLM output was still far from a stable solved problem, *AI2U* achieved striking in-game performance and staging through careful design. This project follows that spirit by treating AI responses as authored signals that can drive readable game actions, emotion bubbles, and scene interactions.

Built with Python, Pygame, Tiled map assets, and an OpenAI-compatible LLM backend, the player can walk around a small pixel-art town, open an in-game phone, chat with an AI character, and let structured LLM responses drive in-world behavior such as navigation targets and emotion bubbles.

![AI Town main menu](showcase/menu.png)

## Demo

<video src="showcase/AI%20town%20demo.mp4" controls width="100%"></video>

If the video does not render in your Markdown viewer, open it directly:

[AI town demo.mp4](showcase/AI%20town%20demo.mp4)

## Highlights

- Python/Pygame client with a resizable window and fullscreen toggle.
- Tiled `.tmx` map rendering using the existing project assets.
- In-game phone chat backed by a local Node LLM gateway.
- Structured JSON responses for AI replies, target furniture ids, and emotion ids.
- Furniture catalog and placement data loaded from CSV.
- Emotion catalog loaded from CSV, with matching pixel-art emotion bubbles drawn above the player.
- Basic AI navigation from phone responses to configured furniture access tiles.
- Main menu, settings panel, LLM test panel, save/settings JSON, and debug response view.

## Run

Install the Python dependencies used by the Pygame client, then start the game:

```powershell
conda activate AI_Town
python python_town/main.py
```

The phone chat and LLM test panel call a local OpenAI-compatible backend. Start it from the repository root:

```powershell
npm install
npm run start:llm
```

The default backend URL is:

```text
http://127.0.0.1:8787
```

API keys and model/provider settings are handled by the Node backend environment configuration.

## Controls

- `WASD`: move the player.
- `Tab`: open or close the phone chat.
- `Enter`: send the phone message when the phone input is focused.
- `Esc`: close panels or return to the menu.
- `Q/E`, `+/-`, or `PageUp/PageDown`: zoom the map camera.
- `Home` or `0`: reset camera zoom.
- Drag the window border: resize the game window.
- `F11` or `Alt+Enter`: toggle fullscreen.

## Project Layout

```text
assets/                 Game resources, tilemaps, sprites, furniture, emotions
art/                    Source or alternate art assets
prompt/                 LLM system prompts
python_town/            Python/Pygame game client
python_town/data/       CSV and JSON data used by the game
server/                 Local OpenAI-compatible LLM gateway
scripts/                Helper scripts
showcase/               README screenshots and demo video
```

For deeper Python-client notes, see [python_town/README.md](python_town/README.md).

## Data-Driven Content

Furniture definitions live in:

```text
python_town/data/furniture_catalog.csv
python_town/data/furniture_placements.csv
```

Emotion bubbles live in:

```text
assets/resources/emotion/
python_town/data/emotion_catalog.csv
```

The phone response schema is configured here:

```text
python_town/data/phone_response_schema.json
```

At runtime, the phone prompt is assembled from the configured schema, furniture catalog, and emotion catalog, so the LLM is asked to return ids that match local game assets.

## Notes

This is a prototype. The repo mixes gameplay systems, LLM experiments, and asset workflows, so many pieces are intentionally data-driven and easy to adjust while iterating.

## Limitations

This project was built in roughly four hours, so many parts are intentionally rough: UI layout, interaction details, prompt design, data authoring, and runtime behavior all have room for improvement.

Future iterations may explore a more convenient table-authoring workflow, as well as algorithms for automatically generating playable scenes.
