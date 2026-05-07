from __future__ import annotations

import pygame

from .config import MIN_SCREEN_SIZE, SCREEN_SIZE, SETTINGS_PATH
from .logging_config import LOGGER
from .map_scene import MapScene
from .menu import MainMenu
from .storage import load_json, save_json


class App:
    def __init__(self):
        pygame.init()
        pygame.key.set_repeat(180, 45)
        pygame.key.stop_text_input()
        pygame.display.set_caption("AI Town Python")
        self.settings = load_json(
            SETTINGS_PATH,
            {
                "providerId": "chatgpt",
                "quality": "standard",
                "serverUrl": "http://127.0.0.1:8787",
                "windowSize": list(SCREEN_SIZE),
                "fullscreen": False,
            },
        )
        self.screen = self.apply_display_settings()
        self.clock = pygame.time.Clock()
        self.running = True
        self.menu = MainMenu(self)
        self.menu.resize(self.screen.get_size())
        self.scene: MainMenu | MapScene = self.menu
        LOGGER.info("App initialized current_scene=%s key_repeat=on text_input=managed", type(self.scene).__name__)

    def apply_display_settings(self) -> pygame.Surface:
        if self.settings.get("fullscreen"):
            screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            width, height = self.normalized_window_size(self.settings.get("windowSize", SCREEN_SIZE))
            self.settings["windowSize"] = [width, height]
            screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
        LOGGER.info(
            "Display mode applied size=%s fullscreen=%s",
            screen.get_size(),
            self.settings.get("fullscreen"),
        )
        return screen

    def normalized_window_size(self, value: object) -> tuple[int, int]:
        try:
            width, height = value  # type: ignore[misc]
            size = (int(width), int(height))
        except (TypeError, ValueError):
            size = SCREEN_SIZE
        return (
            max(MIN_SCREEN_SIZE[0], size[0]),
            max(MIN_SCREEN_SIZE[1], size[1]),
        )

    def set_scene(self, scene: MainMenu | MapScene, reason: str) -> None:
        previous = type(self.scene).__name__ if hasattr(self, "scene") else "<none>"
        pygame.key.stop_text_input()
        self.scene = scene
        resize = getattr(self.scene, "resize", None)
        if resize:
            resize(self.screen.get_size())
        LOGGER.info("Scene changed %s -> %s reason=%s", previous, type(scene).__name__, reason)

    def toggle_fullscreen(self) -> None:
        self.settings["fullscreen"] = not bool(self.settings.get("fullscreen"))
        self.screen = self.apply_display_settings()
        save_json(SETTINGS_PATH, self.settings)
        self.resize_active_scene()

    def resize_window(self, size: tuple[int, int]) -> None:
        if self.settings.get("fullscreen"):
            return
        width, height = self.normalized_window_size(size)
        self.settings["windowSize"] = [width, height]
        self.screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
        save_json(SETTINGS_PATH, self.settings)
        self.resize_active_scene()
        LOGGER.info("Window resized size=%s", (width, height))

    def resize_active_scene(self) -> None:
        resize = getattr(self.scene, "resize", None)
        if resize:
            resize(self.screen.get_size())

    def run(self) -> None:
        LOGGER.info("App run loop started")
        while self.running:
            dt = self.clock.tick(60) / 1000
            for event in pygame.event.get():
                self.log_input_event(event)
                if event.type == pygame.QUIT:
                    LOGGER.info("pygame QUIT received")
                    self.running = False
                elif event.type in (pygame.VIDEORESIZE, pygame.WINDOWRESIZED):
                    self.resize_window(self.event_window_size(event))
                elif event.type == pygame.KEYDOWN and (
                    event.key == pygame.K_F11
                    or (event.key == pygame.K_RETURN and event.mod & pygame.KMOD_ALT)
                ):
                    self.toggle_fullscreen()
                elif event.type == pygame.WINDOWFOCUSGAINED:
                    LOGGER.info("pygame window focus gained")
                    self.scene.handle_event(event)
                elif event.type == pygame.WINDOWFOCUSLOST:
                    LOGGER.info("pygame window focus lost")
                    self.scene.handle_event(event)
                else:
                    self.scene.handle_event(event)
            update = getattr(self.scene, "update", None)
            if update:
                update(dt)
            self.scene.draw(self.screen)
            pygame.display.flip()
        LOGGER.info("App run loop stopped")
        pygame.quit()

    def log_input_event(self, event: pygame.event.Event) -> None:
        if event.type in (pygame.KEYDOWN, pygame.KEYUP):
            LOGGER.debug(
                "App %s key=%s unicode=%r mod=%s scene=%s",
                pygame.event.event_name(event.type),
                pygame.key.name(event.key),
                getattr(event, "unicode", ""),
                getattr(event, "mod", None),
                type(self.scene).__name__,
            )
        elif event.type == pygame.TEXTINPUT:
            LOGGER.debug("App TEXTINPUT text=%r scene=%s", event.text, type(self.scene).__name__)
        elif event.type == pygame.TEXTEDITING:
            LOGGER.debug(
                "App TEXTEDITING text=%r start=%s length=%s scene=%s",
                event.text,
                event.start,
                event.length,
                type(self.scene).__name__,
            )
        elif event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            LOGGER.debug(
                "App %s button=%s pos=%s scene=%s",
                pygame.event.event_name(event.type),
                getattr(event, "button", None),
                getattr(event, "pos", None),
                type(self.scene).__name__,
            )
        elif event.type == pygame.MOUSEWHEEL:
            LOGGER.debug("App MOUSEWHEEL x=%s y=%s scene=%s", event.x, event.y, type(self.scene).__name__)

    def event_window_size(self, event: pygame.event.Event) -> tuple[int, int]:
        size = getattr(event, "size", None)
        if size:
            return int(size[0]), int(size[1])
        width = getattr(event, "x", None) or getattr(event, "w", None)
        height = getattr(event, "y", None) or getattr(event, "h", None)
        if width and height:
            return int(width), int(height)
        return self.screen.get_size()
