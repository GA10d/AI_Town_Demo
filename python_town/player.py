from __future__ import annotations

from pathlib import Path
from typing import Callable

import pygame

from .animation import FrameSequence, load_sprite_frames
from .camera import Camera


CHARACTER_DIRECTIONS = ("down", "left", "right", "up")
PLAYER_MOVE_KEYS = {
    pygame.K_a: pygame.Vector2(-1, 0),
    pygame.K_d: pygame.Vector2(1, 0),
    pygame.K_w: pygame.Vector2(0, -1),
    pygame.K_s: pygame.Vector2(0, 1),
}


class PlayerCharacter:
    def __init__(self, root: Path, position: pygame.Vector2):
        self.position = pygame.Vector2(position)
        self.speed = 76.0
        self.facing = "down"
        self.moving = False
        self.phone_state = "none"
        self.animations: dict[str, FrameSequence] = {}
        self.current_animation_name = ""
        self.current_animation: FrameSequence | None = None
        self.load_animations(root)
        self.set_animation("idle:down")

    @property
    def foot_position(self) -> pygame.Vector2:
        return pygame.Vector2(self.position)

    @property
    def status_label(self) -> str:
        if self.phone_state != "none":
            return f"phone {self.phone_state}"
        return f"{'walk' if self.moving else 'idle'} {self.facing}"

    def load_animations(self, root: Path) -> None:
        for action in ("idle", "walk"):
            fps = 6.0 if action == "idle" else 10.0
            for direction in CHARACTER_DIRECTIONS:
                key = f"{action}:{direction}"
                self.animations[key] = FrameSequence(load_sprite_frames(root / action / direction), fps, True)
        self.animations["phone:begin"] = FrameSequence(load_sprite_frames(root / "phone" / "begin"), 8.0, False)
        self.animations["phone:loop"] = FrameSequence(load_sprite_frames(root / "phone" / "loop"), 8.0, True)
        self.animations["phone:end"] = FrameSequence(load_sprite_frames(root / "phone" / "end"), 8.0, False)

    def set_animation(self, name: str) -> None:
        if name == self.current_animation_name:
            return
        self.current_animation_name = name
        self.current_animation = self.animations[name]
        self.current_animation.reset()

    def request_phone_toggle(self) -> None:
        if self.phone_state == "none":
            self.facing = "down"
            self.moving = False
            self.phone_state = "begin"
            self.set_animation("phone:begin")
        elif self.phone_state == "loop":
            self.phone_state = "end"
            self.set_animation("phone:end")

    def update(
        self,
        dt: float,
        active_keys: set[int],
        world_bounds: tuple[int, int],
        can_stand_at: Callable[[pygame.Vector2], bool] | None = None,
    ) -> None:
        if self.phone_state != "none":
            self.update_phone(dt)
            return

        movement = pygame.Vector2(0, 0)
        for key, direction in PLAYER_MOVE_KEYS.items():
            if key in active_keys:
                movement += direction

        self.moving = movement.length_squared() > 0
        if self.moving:
            movement = movement.normalize()
            self.facing = self.direction_name(movement)
            if can_stand_at:
                self.move_with_collision(movement, self.speed * dt, world_bounds, can_stand_at)
            else:
                self.position += movement * self.speed * dt
                self.clamp_to_world(world_bounds)
            self.set_animation(f"walk:{self.facing}")
        else:
            self.set_animation(f"idle:{self.facing}")

        if self.current_animation:
            self.current_animation.update(dt)

    def move_with_collision(
        self,
        movement: pygame.Vector2,
        distance: float,
        world_bounds: tuple[int, int],
        can_stand_at: Callable[[pygame.Vector2], bool],
    ) -> None:
        if movement.x:
            candidate = self.clamped_position(
                pygame.Vector2(self.position.x + movement.x * distance, self.position.y),
                world_bounds,
            )
            if can_stand_at(candidate):
                self.position.x = candidate.x
        if movement.y:
            candidate = self.clamped_position(
                pygame.Vector2(self.position.x, self.position.y + movement.y * distance),
                world_bounds,
            )
            if can_stand_at(candidate):
                self.position.y = candidate.y

    def update_phone(self, dt: float) -> None:
        if not self.current_animation:
            return
        self.current_animation.update(dt)
        if self.phone_state == "begin" and self.current_animation.finished:
            self.phone_state = "loop"
            self.set_animation("phone:loop")
        elif self.phone_state == "end" and self.current_animation.finished:
            self.phone_state = "none"
            self.facing = "down"
            self.moving = False
            self.set_animation("idle:down")

    def direction_name(self, movement: pygame.Vector2) -> str:
        if abs(movement.x) > abs(movement.y):
            return "right" if movement.x > 0 else "left"
        if movement.y:
            return "down" if movement.y > 0 else "up"
        return self.facing

    def footprint_points(self, position: pygame.Vector2) -> list[pygame.Vector2]:
        half_width = 7
        return [
            pygame.Vector2(position.x - half_width, position.y),
            pygame.Vector2(position.x, position.y),
            pygame.Vector2(position.x + half_width, position.y),
        ]

    def clamped_position(self, position: pygame.Vector2, world_bounds: tuple[int, int]) -> pygame.Vector2:
        image = self.current_animation.image if self.current_animation else None
        sprite_h = image.get_height() if image else 0
        return pygame.Vector2(
            max(0, min(world_bounds[0], position.x)),
            max(sprite_h, min(world_bounds[1], position.y)),
        )

    def clamp_to_world(self, world_bounds: tuple[int, int]) -> None:
        self.position = self.clamped_position(self.position, world_bounds)

    def draw(self, surf: pygame.Surface, camera: Camera) -> None:
        if not self.current_animation:
            return
        image = self.current_animation.image
        size = (
            max(1, round(image.get_width() * camera.zoom)),
            max(1, round(image.get_height() * camera.zoom)),
        )
        if image.get_size() != size:
            image = pygame.transform.scale(image, size)
        foot = camera.world_to_screen(self.foot_position)
        dest = (round(foot.x - size[0] / 2), round(foot.y - size[1]))
        surf.blit(image, dest)

