from __future__ import annotations

import pygame

from .config import TEXT


def font(size: int, bold: bool = False) -> pygame.font.Font:
    names = ["Microsoft YaHei UI", "Microsoft YaHei", "SimHei", "Arial"]
    return pygame.font.SysFont(names, size, bold=bold)


def draw_text(
    surf: pygame.Surface,
    text: str,
    pos: tuple[int, int],
    size: int = 18,
    color: tuple[int, int, int] = TEXT,
    bold: bool = False,
    center: bool = False,
) -> pygame.Rect:
    image = font(size, bold).render(text, True, color)
    rect = image.get_rect()
    rect.center = pos if center else rect.center
    if not center:
        rect.topleft = pos
    surf.blit(image, rect)
    return rect


def wrap_text(text: str, max_width: int, size: int) -> list[str]:
    f = font(size)
    lines: list[str] = []
    for raw in text.splitlines() or [""]:
        current = ""
        tokens = list(raw) if any(ord(ch) > 127 for ch in raw) else raw.split(" ")
        sep = "" if any(ord(ch) > 127 for ch in raw) else " "
        for token in tokens:
            trial = token if not current else current + sep + token
            if f.size(trial)[0] <= max_width:
                current = trial
            else:
                if current:
                    lines.append(current)
                current = token
        lines.append(current)
    return lines
