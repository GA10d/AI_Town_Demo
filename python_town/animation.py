from __future__ import annotations

from pathlib import Path

import pygame


def numeric_frame_key(path: Path) -> tuple[int, int | str]:
    try:
        return (0, int(path.stem))
    except ValueError:
        return (1, path.stem)


def load_sprite_frames(path: Path) -> list[pygame.Surface]:
    frames = [pygame.image.load(str(frame_path)).convert_alpha() for frame_path in sorted(path.glob("*.png"), key=numeric_frame_key)]
    if not frames:
        raise FileNotFoundError(f"No sprite frames found in {path}")
    return frames


class FrameSequence:
    def __init__(self, frames: list[pygame.Surface], fps: float, loop: bool):
        self.frames = frames
        self.frame_time = 1.0 / fps
        self.loop = loop
        self.index = 0
        self.elapsed = 0.0
        self.finished = False

    @property
    def image(self) -> pygame.Surface:
        return self.frames[self.index]

    def reset(self) -> None:
        self.index = 0
        self.elapsed = 0.0
        self.finished = False

    def update(self, dt: float) -> None:
        if self.finished:
            return
        self.elapsed += dt
        while self.elapsed >= self.frame_time and not self.finished:
            self.elapsed -= self.frame_time
            next_index = self.index + 1
            if next_index < len(self.frames):
                self.index = next_index
            elif self.loop:
                self.index = 0
            else:
                self.index = len(self.frames) - 1
                self.finished = True
