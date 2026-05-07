from __future__ import annotations

import math
import random
import time

import pygame

from .camera import Camera
from .config import ACCENT, ART, ASSETS, FURNITURE_CATALOG_PATH, FURNITURE_PLACEMENTS_PATH, GOOD, MUTED, TEXT
from .furniture import FurniturePlacement, load_furniture_catalog, load_furniture_image, load_furniture_placements
from .graphics import draw_text
from .input import WindowsKeyboardFallback
from .logging_config import LOGGER
from .pathfinding import GridCell, astar_path
from .player import PLAYER_MOVE_KEYS, PlayerCharacter
from .phone_chat import PhoneChatOverlay
from .tilemap import TileLayer, parse_tilemap


class MapScene:
    def __init__(self, app: "App"):
        self.app = app
        self.tilemap = parse_tilemap(ASSETS / "tilemap" / "map_test.tmx")
        self.floor_layer = self.require_layer("floor")
        self.wall_layer = self.require_layer("wall")
        self.furniture_catalog = load_furniture_catalog(FURNITURE_CATALOG_PATH)
        self.furniture_placements = load_furniture_placements(FURNITURE_PLACEMENTS_PATH, self.furniture_catalog)
        self.furniture_by_id: dict[str, list[FurniturePlacement]] = {}
        for placement in self.furniture_placements:
            self.furniture_by_id.setdefault(placement.id, []).append(placement)
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
        self.phone_chat = PhoneChatOverlay(self.app.settings, self.furniture_catalog)
        self.camera = Camera(
            position=pygame.Vector2(0, 0),
            zoom=3.0,
            viewport=pygame.Rect(0, 0, *self.app.screen.get_size()),
        )
        self.camera.center_on(self.player.foot_position, self.tilemap.pixel_size)
        self.zoom_speed = 2.0
        self.held_keys: set[int] = set()
        self.phone_toggle_latched = False
        self.keyboard_fallback = WindowsKeyboardFallback()
        self.dragging_camera = False
        self.last_mouse_pos = pygame.Vector2(0, 0)
        self.last_camera_state = (round(self.camera.position.x, 2), round(self.camera.position.y, 2), round(self.camera.zoom, 3))
        self.last_camera_log_at = 0.0
        self.last_fallback_log_at = 0.0
        self.handled_phone_response_count = 0
        self.emotion_image_dir = ASSETS / "resources" / "emotion"
        self.emotion_images: dict[str, pygame.Surface | None] = {}
        self.active_emotion_id = ""
        self.active_emotion_elapsed = 0.0
        self.active_emotion_duration = 6.0
        self.auto_path: list[GridCell] = []
        self.auto_path_index = 0
        self.auto_target_cell: GridCell | None = None
        self.auto_target_furniture_id = ""
        self.auto_target_placement: FurniturePlacement | None = None
        self.action_progress_active = False
        self.action_progress_elapsed = 0.0
        self.action_progress_duration = 1.0
        self.message = "Esc: menu | WASD: move | Tab: phone chat | furniture from CSV"
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
        if self.phone_chat.is_open and event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION, pygame.MOUSEWHEEL):
            handled = self.phone_chat.handle_event(event)
            if self.phone_chat.consume_close_request():
                self.close_phone_chat()
                return
            if handled:
                return
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
        if event.type in (pygame.TEXTINPUT, pygame.TEXTEDITING):
            if self.phone_chat.is_open:
                self.phone_chat.handle_event(event)
                return
            if event.type == pygame.TEXTEDITING:
                return
            self.handle_text_input(event.text)
            return
        if event.type not in (pygame.KEYDOWN, pygame.KEYUP):
            return
        key_name = pygame.key.name(event.key)
        if event.type == pygame.KEYUP:
            self.held_keys.discard(event.key)
            if event.key == pygame.K_TAB:
                self.phone_toggle_latched = False
            LOGGER.debug("MapScene KEYUP key=%s held=%s", key_name, self.describe_held_keys())
            return

        if self.phone_chat.is_open:
            if event.key == pygame.K_ESCAPE:
                self.close_phone_chat()
            elif event.key == pygame.K_TAB:
                if not self.phone_toggle_latched:
                    self.phone_toggle_latched = True
                    self.held_keys.add(event.key)
                    LOGGER.debug("MapScene KEYDOWN key=%s held=%s", key_name, self.describe_held_keys())
                    self.close_phone_chat()
            else:
                self.phone_chat.handle_event(event)
            return

        if self.is_auto_control_active() and event.key in (*PLAYER_MOVE_KEYS.keys(), pygame.K_TAB):
            return

        was_held = event.key in self.held_keys
        self.held_keys.add(event.key)
        LOGGER.debug("MapScene KEYDOWN key=%s held=%s", key_name, self.describe_held_keys())
        if event.key == pygame.K_ESCAPE:
            self.held_keys.clear()
            self.app.set_scene(self.app.menu, "map escape")
            return
        if event.key == pygame.K_TAB and not self.phone_toggle_latched:
            self.phone_toggle_latched = True
            self.open_phone_chat()
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
        fallback_keys = self.keyboard_fallback.pressed_keys()
        self.log_fallback_keys(fallback_keys)
        if pygame.K_TAB not in self.held_keys:
            self.phone_toggle_latched = False
        active_keys = self.held_keys | fallback_keys
        if pygame.K_ESCAPE in fallback_keys:
            self.keyboard_fallback.last_keys.clear()
            self.app.set_scene(self.app.menu, "windows keyboard fallback escape")
            return
        if pygame.K_HOME in fallback_keys or pygame.K_0 in fallback_keys:
            self.camera.zoom = 3.0
            self.camera.center_on(self.player.foot_position, self.tilemap.pixel_size)
            self.log_camera_state("fallback reset")

        self.consume_phone_responses()
        self.update_active_emotion(dt)
        auto_active = self.is_auto_control_active()
        control_keys = set() if self.phone_chat.is_open or auto_active else active_keys
        if self.auto_path:
            self.update_auto_navigation(dt)
        elif self.action_progress_active:
            self.update_action_progress(dt)
        else:
            self.player.update(dt, control_keys, self.tilemap.pixel_size, self.is_player_position_walkable)

        if not self.phone_chat.is_open and not auto_active:
            if pygame.K_PAGEUP in active_keys or pygame.K_e in active_keys or pygame.K_EQUALS in active_keys or pygame.K_KP_PLUS in active_keys:
                self.camera.set_zoom(self.camera.zoom + self.zoom_speed * dt, self.tilemap.pixel_size)
            elif pygame.K_PAGEDOWN in active_keys or pygame.K_q in active_keys or pygame.K_MINUS in active_keys or pygame.K_KP_MINUS in active_keys:
                self.camera.set_zoom(self.camera.zoom - self.zoom_speed * dt, self.tilemap.pixel_size)
        self.camera.center_on(self.player.foot_position, self.tilemap.pixel_size)
        self.log_camera_state("follow")

    def open_phone_chat(self) -> None:
        self.phone_chat.open()
        self.player.force_start_phone_call()
        LOGGER.info("MapScene phone chat opened state=%s", self.player.phone_state)

    def resize(self, size: tuple[int, int]) -> None:
        self.camera.viewport = pygame.Rect(0, 0, *size)
        self.camera.center_on(self.player.foot_position, self.tilemap.pixel_size)
        self.phone_chat.resize(size)

    def close_phone_chat(self) -> None:
        self.phone_chat.close()
        self.phone_toggle_latched = False
        self.held_keys.discard(pygame.K_TAB)
        self.player.end_phone_call()
        LOGGER.info("MapScene phone chat closed state=%s", self.player.phone_state)

    def toggle_phone_chat(self) -> None:
        if self.phone_chat.is_open:
            self.close_phone_chat()
        else:
            self.open_phone_chat()

    def is_auto_control_active(self) -> bool:
        return bool(self.auto_path) or self.action_progress_active

    def consume_phone_responses(self) -> None:
        responses = self.phone_chat.structured_responses
        if self.handled_phone_response_count >= len(responses):
            return

        pending = responses[self.handled_phone_response_count :]
        self.handled_phone_response_count = len(responses)
        for response in pending:
            self.show_response_emotion(response)
            furniture_id = self.response_furniture_id(response)
            if furniture_id:
                self.start_navigation_to_furniture(furniture_id)

    def show_response_emotion(self, response: dict) -> None:
        value = response.get("emotion")
        if value is None:
            return
        emotion_id = str(value).strip()
        if not emotion_id or emotion_id.lower() == "neutral":
            self.clear_active_emotion()
            return
        if not self.load_emotion_image(emotion_id):
            LOGGER.warning("AI emotion id has no image asset: %s", emotion_id)
            self.clear_active_emotion()
            return
        self.active_emotion_id = emotion_id
        self.active_emotion_elapsed = 0.0
        LOGGER.info("AI emotion bubble shown id=%s", emotion_id)

    def clear_active_emotion(self) -> None:
        self.active_emotion_id = ""
        self.active_emotion_elapsed = 0.0

    def update_active_emotion(self, dt: float) -> None:
        if not self.active_emotion_id:
            return
        self.active_emotion_elapsed += dt
        if self.active_emotion_elapsed >= self.active_emotion_duration:
            self.clear_active_emotion()

    def load_emotion_image(self, emotion_id: str) -> pygame.Surface | None:
        if emotion_id not in self.emotion_images:
            path = self.emotion_image_dir / f"{emotion_id}.png"
            if path.exists():
                self.emotion_images[emotion_id] = pygame.image.load(str(path)).convert_alpha()
            else:
                self.emotion_images[emotion_id] = None
        return self.emotion_images[emotion_id]

    def response_furniture_id(self, response: dict) -> str:
        value = response.get("target_furniture_id")
        if value is None:
            return ""
        furniture_id = str(value).strip()
        if not furniture_id or furniture_id.lower() == "null":
            return ""
        return furniture_id

    def start_navigation_to_furniture(self, furniture_id: str) -> None:
        placements = self.furniture_by_id.get(furniture_id)
        if not placements:
            self.message = f"No placement configured for furniture: {furniture_id}"
            LOGGER.warning("AI navigation target has no placement: %s", furniture_id)
            return

        candidates = [
            (placement, access_tile)
            for placement in placements
            for access_tile in placement.access_tiles
            if self.is_standable_cell(*access_tile)
        ]
        if not candidates:
            self.message = f"No walkable access tile for furniture: {furniture_id}"
            LOGGER.warning("AI navigation target has no walkable access tile: %s", furniture_id)
            return

        random.shuffle(candidates)
        start = self.world_to_cell(self.player.foot_position)
        for placement, target_cell in candidates:
            path = astar_path(
                start,
                target_cell,
                self.tilemap.width,
                self.tilemap.height,
                self.is_standable_cell,
            )
            if path:
                self.begin_auto_navigation(furniture_id, placement, target_cell, path)
                return

        self.message = f"No path found to furniture: {furniture_id}"
        LOGGER.warning("AI navigation could not path to furniture=%s from=%s", furniture_id, start)

    def begin_auto_navigation(
        self,
        furniture_id: str,
        placement: FurniturePlacement,
        target_cell: GridCell,
        path: list[GridCell],
    ) -> None:
        self.auto_path = path
        self.auto_path_index = 0
        self.auto_target_cell = target_cell
        self.auto_target_furniture_id = furniture_id
        self.auto_target_placement = placement
        self.action_progress_active = False
        self.action_progress_elapsed = 0.0
        self.phone_chat.set_input_focused(False)
        self.held_keys.difference_update(PLAYER_MOVE_KEYS.keys())
        if self.player.phone_state != "none":
            self.player.end_phone_call()
        self.message = f"AI navigating to {furniture_id} at {target_cell}"
        LOGGER.info(
            "AI navigation start furniture=%s target=%s path_len=%s",
            furniture_id,
            target_cell,
            len(path),
        )

    def update_auto_navigation(self, dt: float) -> None:
        if not self.auto_path:
            return
        if self.auto_path_index >= len(self.auto_path):
            self.complete_auto_navigation()
            return

        waypoint_cell = self.auto_path[self.auto_path_index]
        waypoint = self.cell_center(waypoint_cell)
        reached_waypoint = self.player.update_navigation(
            dt,
            waypoint,
            self.tilemap.pixel_size,
            self.is_player_position_walkable,
        )
        if not reached_waypoint:
            return

        self.auto_path_index += 1
        if self.auto_path_index >= len(self.auto_path):
            self.complete_auto_navigation()

    def complete_auto_navigation(self) -> None:
        self.face_player_toward_placement(self.auto_target_placement, self.auto_target_cell)
        self.auto_path = []
        self.auto_path_index = 0
        self.action_progress_active = True
        self.action_progress_elapsed = 0.0
        self.player.moving = False
        self.player.set_animation(f"idle:{self.player.facing}")
        self.message = f"AI interacting with {self.auto_target_furniture_id}"
        LOGGER.info(
            "AI navigation arrived furniture=%s cell=%s",
            self.auto_target_furniture_id,
            self.auto_target_cell,
        )

    def update_action_progress(self, dt: float) -> None:
        self.action_progress_elapsed += dt
        self.player.update(dt, set(), self.tilemap.pixel_size, self.is_player_position_walkable)
        if self.action_progress_elapsed >= self.action_progress_duration:
            self.action_progress_active = False
            self.message = f"AI finished interacting with {self.auto_target_furniture_id}"
            LOGGER.info("AI action complete furniture=%s", self.auto_target_furniture_id)

    def face_player_toward_placement(
        self,
        placement: FurniturePlacement | None,
        access_cell: GridCell | None,
    ) -> None:
        if not placement or not access_cell:
            return
        access = self.cell_center(access_cell)
        nearest = min(
            (self.cell_center(cell) for cell in placement.covered_cells),
            key=lambda point: (point - access).length_squared(),
        )
        delta = nearest - access
        if delta.length_squared():
            self.player.facing = self.player.direction_name(delta)

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

    def cell_center(self, cell: GridCell) -> pygame.Vector2:
        x, y = cell
        return pygame.Vector2(
            (x + 0.5) * self.tilemap.tile_width,
            (y + 0.5) * self.tilemap.tile_height,
        )

    def is_walkable_cell(self, x: int, y: int) -> bool:
        if x < 0 or y < 0 or x >= self.tilemap.width or y >= self.tilemap.height:
            return False
        has_floor = self.floor_layer.gid_at(x, y) != 0
        has_wall = self.wall_layer.gid_at(x, y) != 0
        has_blocking_furniture = (x, y) in self.furniture_blocked_cells
        return has_floor and not has_wall and not has_blocking_furniture

    def is_standable_cell(self, x: int, y: int) -> bool:
        return self.is_walkable_cell(x, y) and self.is_player_position_walkable(self.cell_center((x, y)))

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

    def draw_action_progress(self, surf: pygame.Surface) -> None:
        if not self.action_progress_active or not self.player.current_animation:
            return

        progress = min(1.0, self.action_progress_elapsed / self.action_progress_duration)
        image = self.player.current_animation.image
        foot = self.camera.world_to_screen(self.player.foot_position)
        sprite_height = image.get_height() * self.camera.zoom
        bar_width = 48
        bar_height = 7
        rect = pygame.Rect(
            round(foot.x - bar_width / 2),
            round(foot.y - sprite_height - 14),
            bar_width,
            bar_height,
        )
        pygame.draw.rect(surf, (0, 0, 0), rect.inflate(4, 4), border_radius=4)
        pygame.draw.rect(surf, (42, 45, 48), rect, border_radius=3)
        fill = rect.copy()
        fill.width = max(1, round(rect.width * progress))
        pygame.draw.rect(surf, GOOD, fill, border_radius=3)
        pygame.draw.rect(surf, TEXT, rect, 1, border_radius=3)

    def draw_active_emotion(self, surf: pygame.Surface) -> None:
        if not self.active_emotion_id or not self.player.current_animation:
            return
        image = self.load_emotion_image(self.active_emotion_id)
        if not image:
            return

        player_image = self.player.current_animation.image
        foot = self.camera.world_to_screen(self.player.foot_position)
        player_height = player_image.get_height() * self.camera.zoom
        bubble_size = (
            max(1, round(image.get_width() * self.camera.zoom)),
            max(1, round(image.get_height() * self.camera.zoom)),
        )
        bubble = pygame.transform.scale(image, bubble_size) if image.get_size() != bubble_size else image
        gap = max(0, round(-70 * self.camera.zoom))
        dest = (
            round(foot.x - bubble_size[0] / 2),
            round(foot.y - player_height - gap - bubble_size[1]),
        )
        surf.blit(bubble, dest)

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
        self.draw_active_emotion(surf)
        self.draw_action_progress(surf)
        self.phone_chat.draw(surf)

        draw_text(surf, "AI Town / test.scene", (32, 28), 24, TEXT, True)
        draw_text(surf, f"TMX: {self.tilemap.width}x{self.tilemap.height}, layers: {', '.join(layer.name for layer in self.tilemap.layers)}", (32, 62), 15, MUTED)
        draw_text(surf, f"camera: x={self.camera.position.x:.1f}, y={self.camera.position.y:.1f}, zoom={self.camera.zoom:.2f}", (32, 88), 15, ACCENT)
        draw_text(surf, f"player: x={self.player.position.x:.1f}, y={self.player.position.y:.1f}, {self.player.status_label}", (32, 112), 15, GOOD)
        draw_text(surf, f"furniture: {len(self.furniture_placements)} | keyboard fallback: {'on' if self.keyboard_fallback.enabled else 'off'}", (32, 136), 15, MUTED)
        draw_text(surf, self.message, (32, 596), 16, (132, 118, 96))
