from __future__ import annotations

import ctypes

import pygame

from .config import IS_WINDOWS


class WindowsKeyboardFallback:
    KEY_CODES = {
        pygame.K_w: 0x57,
        pygame.K_a: 0x41,
        pygame.K_s: 0x53,
        pygame.K_d: 0x44,
        pygame.K_j: 0x4A,
        pygame.K_q: 0x51,
        pygame.K_e: 0x45,
        pygame.K_LEFT: 0x25,
        pygame.K_UP: 0x26,
        pygame.K_RIGHT: 0x27,
        pygame.K_DOWN: 0x28,
        pygame.K_PAGEUP: 0x21,
        pygame.K_PAGEDOWN: 0x22,
        pygame.K_HOME: 0x24,
        pygame.K_ESCAPE: 0x1B,
        pygame.K_0: 0x30,
        pygame.K_EQUALS: 0xBB,
        pygame.K_MINUS: 0xBD,
        pygame.K_KP_PLUS: 0x6B,
        pygame.K_KP_MINUS: 0x6D,
    }

    def __init__(self) -> None:
        self.enabled = IS_WINDOWS and hasattr(ctypes, "windll")
        self.last_keys: set[int] = set()

    def pressed_keys(self) -> set[int]:
        if not self.enabled:
            return set()
        pressed: set[int] = set()
        user32 = ctypes.windll.user32
        for pygame_key, virtual_key in self.KEY_CODES.items():
            if user32.GetAsyncKeyState(virtual_key) & 0x8000:
                pressed.add(pygame_key)
        return pressed
