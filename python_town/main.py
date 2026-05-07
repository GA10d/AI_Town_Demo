from __future__ import annotations

import sys
from pathlib import Path

import pygame

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from python_town.app import App


if __name__ == "__main__":
    try:
        App().run()
    except Exception as exc:  # noqa: BLE001
        pygame.quit()
        print(f"AI Town Python crashed: {exc}", file=sys.stderr)
        raise
