from __future__ import annotations

import math
import time

import pygame

from .camera import Camera
from .config import ACCENT, ART, ASSETS, FURNITURE_CATALOG_PATH, FURNITURE_PLACEMENTS_PATH, GOOD, MUTED, SCREEN_SIZE, TEXT
from .furniture import FurniturePlacement, load_furniture_catalog, load_furniture_image, load_furniture_placements
from .graphics import draw_text
from .input import WindowsKeyboardFallback
from .logging_config import LOGGER
from .player import PlayerCharacter
from .tilemap import TileLayer, parse_tilemap


class MapScene:
    def __init__(self, app: "App"):
        self.app = app
        self.tilemap = parse_tilemap(ASSETS / "tilemap" / "map_test.tmx")
        self.floor_layer = self.require_layer("floor")
        self.wall_layer = self.require_layer("wall")
        self.furniture_catalog = load_furniture_catalog(FURNITURE_CATALOG_PATH)
        self.furniture_placements = load_furniture_placements(FURNITURE_PLACEMENTS_PATH, self.furniture_catalog)
        self.furniture_blocked_cells = {
            cell
            for placement in self.furniture_placements
            if placement.blocks_movement
            for cell in placement.covered_cells
        }
        self.furniture_images = {
            placement.id: load_furniture_image(placement.id)
            for placement in self.furniture_placements
        }
        self.player = PlayerCharacter(
            ART / "character" / "character_test",
            pygame.Vector2(self.tilemap.tile_width * 6, self.tilemap.tile_height * 6),
        )
        self.camera = Camera(
            position=pygame.Vector2(0, 0),
            zoom=3.0,
            viewport=pygame.Rect(0, 0, *SCREEN_SIZE),
        )
        self.camera.center_on(self.player.foot_position, self.tilemap.pixel_size)
        self.zoom_speed = 2.0
        self.held_keys: set[int] = set()
        self.keyboard_fallback = WindowsKeyboardFallback()
        self.dragging_camera = False
        self.last_mouse_pos = pygame.Vector2(0, 0)
        self.last_camera_state = (round(self.camera.position.x, 2), round(self.camera.position.y, 2), round(self.camera.zoom, 3))
        self.last_camera_log_at = 0.0
        self.last_fallback_log_at = 0.0
        self.message = "Esc: menu | WASD: move | J: phone | furniture from CSV"
        LOGGER.info(
            "MapScene initialized map=%sx%s pixels=%s player=(%.2f, %.2f) camera=(%.2f, %.2f, %.2f) walkable=%s furniture=%s keyboard_fallback=%s",
            self.tilemap.width,
            self.tilemap.height,
            self.tilemap.pixel_size,
            self.player.position.x,
            self.player.position.y,
            self.camera.position.x,
            self.camera.position.y,
            self.camera.zoom,
            sum(
                1
                for y in range(self.tilemap.height)
                for x in range(self.tilemap.width)
                if self.is_walkable_cell(x, y)
            ),
            len(self.furniture_placements),
            self.keyboard_fallback.enabled,
        )

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.handle_mouse_button_down(event)
            return
        if event.type == pygame.MOUSEBUTTONUP:
            self.handle_mouse_button_up(event)
            return
        if event.type == pygame.MOUSEMOTION:
            self.handle_mouse_motion(event)
            return
        if event.type == pygame.MOUSEWHEEL:
            self.handle_mouse_wheel(event)
            return
        if event.type == pygame.TEXTINPUT:
            self.handle_text_input(event.text)
            return
        if event.type not in (pygame.KEYDOWN, pygame.KEYUP):
            return
        key_name = pygame.key.name(event.key)
        if event.type == pygame.KEYUP:
            self.held_keys.discard(event.key)
            LOGGER.debug("MapScene KEYUP key=%s held=%s", key_name, self.describe_held_keys())
            return

        was_held = event.key in self.held_keys
        self.held_keys.add(event.key)
        LOGGER.debug("MapScene KEYDOWN key=%s held=%s", key_name, self.describe_held_keys())
        if event.key == pygame.K_ESCAPE:
            self.held_keys.clear()
            self.app.set_scene(self.app.menu, "map escape")
            return
        if event.key == pygame.K_j and not was_held:
            self.player.request_phone_toggle()
            LOGGER.info("MapScene player phone toggle state=%s", self.player.phone_state)
            return
        if event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS, pygame.K_e):
            self.camera.set_zoom(self.camera.zoom * 1.15, self.tilemap.pixel_size)
            self.camera.center_on(self.player.foot_position, self.tilemap.pixel_size)
            self.log_camera_state("zoom keydown")
        elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS, pygame.K_q):
            self.camera.set_zoom(self.camera.zoom / 1.15, self.tilemap.pixel_size)
            self.camera.center_on(self.player.foot_position, self.tilemap.pixel_size)
            self.log_camera_state("zoom keydown")
        elif event.key in (pygame.K_0, pygame.K_HOME):
            self.camera.zoom = 3.0
            self.camera.center_on(self.player.foot_position, self.tilemap.pixel_size)
            self.log_camera_state("reset")

    def update(self, dt: float) -> None:
        previous_fallback_keys = set(self.keyboard_fallback.last_keys)
        fallback_keys = self.keyboard_fallback.pressed_keys()
        self.log_fallback_keys(fallback_keys)
        active_keys = self.held_keys | fallback_keys
        if pygame.K_ESCAPE in fallback_keys:
            self.keyboard_fallback.last_keys.clear()
            self.app.set_scene(self.app.menu, "windows keyboard fallback escape")
            return
        new_fallback_keys = fallback_keys - previous_fallback_keys
        if pygame.K_j in new_fallback_keys and pygame.K_j not in self.held_keys:
            self.player.request_phone_toggle()
            LOGGER.info("MapScene fallback player phone toggle state=%s", self.player.phone_state)
        if pygame.K_HOME in fallback_keys or pygame.K_0 in fallback_keys:
            self.camera.zoom = 3.0
            self.camera.center_on(self.player.foot_position, self.tilemap.pixel_size)
            self.log_camera_state("fallback reset")
        self.player.update(dt, active_keys, self.tilemap.pixel_size, self.is_player_position_walkable)
        if pygame.K_PAGEUP in active_keys or pygame.K_e in active_keys or pygame.K_EQUALS in active_keys or pygame.K_KP_PLUS in active_keys:
            self.camera.set_zoom(self.camera.zoom + self.zoom_speed * dt, self.tilemap.pixel_size)
        elif pygame.K_PAGEDOWN in active_keys or pygame.K_q in active_keys or pygame.K_MINUS in active_keys or pygame.K_KP_MINUS in active_keys:
            self.camera.set_zoom(self.camera.zoom - self.zoom_speed * dt, self.tilemap.pixel_size)
        self.camera.center_on(self.player.foot_position, self.tilemap.pixel_size)
        self.log_camera_state("follow")

    def log_fallback_keys(self, keys: set[int]) -> None:
        now = time.time()
        if not keys and not self.keyboard_fallback.last_keys:
            return
        if keys != self.keyboard_fallback.last_keys or (keys and now - self.last_fallback_log_at >= 0.5):
            LOGGER.debug("MapScene WINDOWS_KEYS held=%s", sorted(pygame.key.name(key) for key in keys))
            self.keyboard_fallback.last_keys = set(keys)
            self.last_fallback_log_at = now

    def handle_mouse_button_down(self, event: pygame.event.Event) -> None:
        if event.button in (1, 2, 3):
            self.dragging_camera = True
            self.last_mouse_pos = pygame.Vector2(event.pos)
            LOGGER.debug("MapScene mouse drag start button=%s pos=%s", event.button, event.pos)

    def handle_mouse_button_up(self, event: pygame.event.Event) -> None:
        if event.button in (1, 2, 3):
            self.dragging_camera = False
            LOGGER.debug("MapScene mouse drag stop button=%s pos=%s", event.button, event.pos)

    def handle_mouse_motion(self, event: pygame.event.Event) -> None:
        if not self.dragging_camera:
            return
        pos = pygame.Vector2(event.pos)
        delta = pos - self.last_mouse_pos
        self.last_mouse_pos = pos
        if delta.length_squared():
            self.camera.move(-delta / self.camera.zoom, self.tilemap.pixel_size)
            self.log_camera_state("mouse drag")

    def handle_mouse_wheel(self, event: pygame.event.Event) -> None:
        if event.y:
            factor = 1.12 ** event.y
            mouse_pos = pygame.mouse.get_pos()
            self.camera.set_zoom(self.camera.zoom * factor, self.tilemap.pixel_size, mouse_pos)
            self.log_camera_state("mouse wheel")

    def handle_text_input(self, text: str) -> None:
        LOGGER.debug("MapScene TEXTINPUT text=%r", text)
        for char in text.lower():
            if char in ("e", "+", "="):
                self.camera.set_zoom(self.camera.zoom * 1.15, self.tilemap.pixel_size)
                self.camera.center_on(self.player.foot_position, self.tilemap.pixel_size)
                self.log_camera_state("text zoom")
            elif char in ("q", "-", "_"):
                self.camera.set_zoom(self.camera.zoom / 1.15, self.tilemap.pixel_size)
                self.camera.center_on(self.player.foot_position, self.tilemap.pixel_size)
                self.log_camera_state("text zoom")

    def require_layer(self, name: str) -> TileLayer:
        layer = self.tilemap.layer_named(name)
        if not layer:
            raise ValueError(f"Required TMX layer not found: {name}")
        return layer

    def world_to_cell(self, point: pygame.Vector2 | tuple[float, float]) -> tuple[int, int]:
        world = pygame.Vector2(point)
        return (
            math.floor(world.x / self.tilemap.tile_width),
            math.floor(world.y / self.tilemap.tile_height),
        )

    def is_walkable_cell(self, x: int, y: int) -> bool:
        if x < 0 or y < 0 or x >= self.tilemap.width or y >= self.tilemap.height:
            return False
        has_floor = self.floor_layer.gid_at(x, y) != 0
        has_wall = self.wall_layer.gid_at(x, y) != 0
        has_blocking_furniture = (x, y) in self.furniture_blocked_cells
        return has_floor and not has_wall and not has_blocking_furniture

    def is_walkable_world_point(self, point: pygame.Vector2 | tuple[float, float]) -> bool:
        return self.is_walkable_cell(*self.world_to_cell(point))

    def is_player_position_walkable(self, position: pygame.Vector2) -> bool:
        return all(self.is_walkable_world_point(point) for point in self.player.footprint_points(position))

    def furniture_world_rect(self, placement: FurniturePlacement) -> tuple[pygame.Vector2, pygame.Vector2]:
        x, bottom_y = placement.cell
        width, height = placement.size
        top_y = bottom_y - height + 1
        top_left = pygame.Vector2(x * self.tilemap.tile_width, top_y * self.tilemap.tile_height)
        bottom_right = pygame.Vector2((x + width) * self.tilemap.tile_width, (bottom_y + 1) * self.tilemap.tile_height)
        return top_left, bottom_right

    def draw_furniture(self, surf: pygame.Surface) -> None:
        for placement in self.furniture_placements:
            top_left, bottom_right = self.furniture_world_rect(placement)
            screen_top_left = self.camera.world_to_screen(top_left)
            screen_bottom_right = self.camera.world_to_screen(bottom_right)
            left = round(screen_top_left.x)
            top = round(screen_top_left.y)
            right = round(screen_bottom_right.x)
            bottom = round(screen_bottom_right.y)
            rect = pygame.Rect(left, top, max(1, right - left), max(1, bottom - top))

            image = self.furniture_images.get(placement.id)
            if image:
                if image.get_size() != rect.size:
                    image = pygame.transform.scale(image, rect.size)
                surf.blit(image, rect.topleft)
            else:
                pygame.draw.rect(surf, (72, 54, 83), rect)
                pygame.draw.rect(surf, (211, 174, 236), rect, max(1, round(self.camera.zoom)))

    def describe_held_keys(self) -> list[str]:
        return sorted(pygame.key.name(key) for key in self.held_keys)

    def log_camera_state(self, reason: str) -> None:
        state = (round(self.camera.position.x, 2), round(self.camera.position.y, 2), round(self.camera.zoom, 3))
        now = time.time()
        if state != self.last_camera_state and (reason != "update" or now - self.last_camera_log_at >= 0.2):
            LOGGER.info("MapScene camera %s -> x=%.2f y=%.2f zoom=%.3f held=%s", reason, *state, self.describe_held_keys())
            self.last_camera_state = state
            self.last_camera_log_at = now

    def draw(self, surf: pygame.Surface) -> None:
        surf.fill((11, 13, 14))
        map_rect_pos = self.camera.world_to_screen((0, 0))
        map_rect_size = pygame.Vector2(self.tilemap.pixel_size) * self.camera.zoom
        map_rect = pygame.Rect(round(map_rect_pos.x), round(map_rect_pos.y), round(map_rect_size.x), round(map_rect_size.y))
        pygame.draw.rect(surf, (18, 20, 22), map_rect.inflate(48, 48), border_radius=6)
        pygame.draw.rect(surf, (54, 58, 62), map_rect.inflate(48, 48), 2, border_radius=6)

        for layer in self.tilemap.layers:
            for index, gid in enumerate(layer.gids):
                if gid == 0:
                    continue
                tileset = self.tilemap.tileset_for_gid(gid)
                if not tileset:
                    continue
                x = index % layer.width
                y = index // layer.width
                src = tileset.tile_rect(gid)
                tile = tileset.image.subsurface(src)
                top_left = self.camera.world_to_screen((x * self.tilemap.tile_width, y * self.tilemap.tile_height))
                bottom_right = self.camera.world_to_screen(((x + 1) * self.tilemap.tile_width, (y + 1) * self.tilemap.tile_height))
                left = round(top_left.x)
                top = round(top_left.y)
                right = round(bottom_right.x)
                bottom = round(bottom_right.y)
                tile_size = (
                    max(1, right - left),
                    max(1, bottom - top),
                )
                if tile.get_size() != tile_size:
                    tile = pygame.transform.scale(tile, tile_size)
                surf.blit(tile, (left, top))

        self.draw_furniture(surf)
        self.player.draw(surf, self.camera)

        draw_text(surf, "AI Town / test.scene", (32, 28), 24, TEXT, True)
        draw_text(surf, f"TMX: {self.tilemap.width}x{self.tilemap.height}, layers: {', '.join(layer.name for layer in self.tilemap.layers)}", (32, 62), 15, MUTED)
        draw_text(surf, f"camera: x={self.camera.position.x:.1f}, y={self.camera.position.y:.1f}, zoom={self.camera.zoom:.2f}", (32, 88), 15, ACCENT)
        draw_text(surf, f"player: x={self.player.position.x:.1f}, y={self.player.position.y:.1f}, {self.player.status_label}", (32, 112), 15, GOOD)
        draw_text(surf, f"furniture: {len(self.furniture_placements)} | keyboard fallback: {'on' if self.keyboard_fallback.enabled else 'off'}", (32, 136), 15, MUTED)
        draw_text(surf, self.message, (32, 596), 16, (132, 118, 96))
