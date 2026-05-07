from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
ART = ROOT / "art"
SETTINGS_PATH = ROOT / "python_town" / "settings.json"
SAVE_PATH = ROOT / "python_town" / "save.json"
LOG_PATH = ROOT / "python_town" / "logs" / "ai_town.log"
FURNITURE_CATALOG_PATH = ROOT / "python_town" / "data" / "furniture_catalog.csv"
FURNITURE_PLACEMENTS_PATH = ROOT / "python_town" / "data" / "furniture_placements.csv"
PHONE_RESPONSE_SCHEMA_PATH = ROOT / "python_town" / "data" / "phone_response_schema.json"
FURNITURE_IMAGE_DIRS = [
    ASSETS / "resources" / "furniture",
    ART / "furniture",
]

SCREEN_SIZE = (960, 640)
BG = (7, 8, 8)
PANEL = (18, 20, 22)
PANEL_2 = (30, 33, 36)
TEXT = (236, 238, 240)
MUTED = (151, 174, 166)
ACCENT = (236, 174, 88)
GOOD = (132, 211, 151)
WARN = (236, 174, 88)

PROVIDERS = [
    ("chatgpt", "ChatGPT"),
    ("deepseek", "DeepSeek"),
    ("gemini", "Gemini"),
    ("doubao", "Doubao"),
    ("qwen", "Qwen"),
    ("custom-openai-compatible", "Custom"),
]
QUALITIES = [("fast", "Fast"), ("standard", "Standard")]
IS_WINDOWS = sys.platform.startswith("win")
