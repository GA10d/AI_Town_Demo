from __future__ import annotations

from dataclasses import dataclass

import pygame


@dataclass
class Camera:
    position: pygame.Vector2
    zoom: float
    viewport: pygame.Rect

    min_zoom: float = 1.0
    max_zoom: float = 5.0

    def world_to_screen(self, point: pygame.Vector2 | tuple[float, float]) -> pygame.Vector2:
        world = pygame.Vector2(point)
        return (world - self.position) * self.zoom + pygame.Vector2(self.viewport.topleft)

    def screen_to_world(self, point: pygame.Vector2 | tuple[float, float]) -> pygame.Vector2:
        screen = pygame.Vector2(point) - pygame.Vector2(self.viewport.topleft)
        return screen / self.zoom + self.position

    def move(self, delta: pygame.Vector2, world_bounds: tuple[int, int]) -> None:
        self.position += delta
        self.clamp_to_world(world_bounds)

    def set_zoom(self, zoom: float, world_bounds: tuple[int, int], pivot: tuple[float, float] | None = None) -> None:
        pivot = pivot or self.viewport.center
        before = self.screen_to_world(pivot)
        self.zoom = max(self.min_zoom, min(self.max_zoom, zoom))
        after = self.screen_to_world(pivot)
        self.position += before - after
        self.clamp_to_world(world_bounds)

    def center_on(self, point: pygame.Vector2 | tuple[float, float], world_bounds: tuple[int, int]) -> None:
        world = pygame.Vector2(point)
        view_size = pygame.Vector2(self.viewport.size) / self.zoom
        self.position = world - view_size / 2
        self.clamp_to_world(world_bounds)

    def clamp_to_world(self, world_bounds: tuple[int, int]) -> None:
        view_w = self.viewport.width / self.zoom
        view_h = self.viewport.height / self.zoom
        max_x = max(0, world_bounds[0] - view_w)
        max_y = max(0, world_bounds[1] - view_h)
        self.position.x = max(0, min(max_x, self.position.x))
        self.position.y = max(0, min(max_y, self.position.y))
