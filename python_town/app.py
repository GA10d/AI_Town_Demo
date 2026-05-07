from __future__ import annotations

import pygame

from .config import SCREEN_SIZE, SETTINGS_PATH
from .logging_config import LOGGER
from .map_scene import MapScene
from .menu import MainMenu
from .storage import load_json


class App:
    def __init__(self):
        pygame.init()
        pygame.key.set_repeat(180, 45)
        pygame.key.start_text_input()
        pygame.display.set_caption("AI Town Python")
        self.screen = pygame.display.set_mode(SCREEN_SIZE)
        self.clock = pygame.time.Clock()
        self.settings = load_json(
            SETTINGS_PATH,
            {"providerId": "chatgpt", "quality": "standard", "serverUrl": "http://127.0.0.1:8787"},
        )
        self.running = True
        self.menu = MainMenu(self)
        self.scene: MainMenu | MapScene = self.menu
        LOGGER.info("App initialized current_scene=%s key_repeat=on text_input=on", type(self.scene).__name__)

    def set_scene(self, scene: MainMenu | MapScene, reason: str) -> None:
        previous = type(self.scene).__name__ if hasattr(self, "scene") else "<none>"
        self.scene = scene
        LOGGER.info("Scene changed %s -> %s reason=%s", previous, type(scene).__name__, reason)

    def run(self) -> None:
        LOGGER.info("App run loop started")
        while self.running:
            dt = self.clock.tick(60) / 1000
            for event in pygame.event.get():
                self.log_input_event(event)
                if event.type == pygame.QUIT:
                    LOGGER.info("pygame QUIT received")
                    self.running = False
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

