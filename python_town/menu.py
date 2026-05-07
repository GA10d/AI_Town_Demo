from __future__ import annotations

import threading
import time
from typing import Callable

import pygame

from .config import ASSETS, BG, GOOD, MUTED, PANEL, PANEL_2, PROVIDERS, QUALITIES, SAVE_PATH, SCREEN_SIZE, SETTINGS_PATH, TEXT, WARN
from .graphics import draw_text, wrap_text
from .llm import cycle_setting, label_for, llm_generate, llm_health
from .logging_config import LOGGER
from .map_scene import MapScene
from .storage import save_json


class Button:
    def __init__(self, label: str, detail: str, action: Callable[[], None]):
        self.label = label
        self.detail = detail
        self.action = action
        self.rect = pygame.Rect(0, 0, 220, 34)

    def draw(self, surf: pygame.Surface, active: bool) -> None:
        fill = (44, 48, 52) if active else PANEL_2
        stroke = TEXT if active else (82, 88, 92)
        pygame.draw.rect(surf, fill, self.rect, border_radius=5)
        pygame.draw.rect(surf, stroke, self.rect, 2, border_radius=5)
        draw_text(surf, self.label, (self.rect.x + 34, self.rect.y + 7), 18, TEXT if active else (164, 151, 126))
        if active:
            pts = [(self.rect.x + 12, self.rect.centery), (self.rect.x + 22, self.rect.y + 9), (self.rect.x + 22, self.rect.bottom - 9)]
            pygame.draw.polygon(surf, TEXT, pts)


class MainMenu:
    def __init__(self, app: "App"):
        self.app = app
        self.buttons = [
            Button("Start", "建立新的小镇日程", self.start),
            Button("Continue", "读取本地存档状态", self.continue_game),
            Button("LLM Test", "和当前选择的 AI 聊天", self.open_chat),
            Button("Settings", "音量、画面和调试选项", self.toggle_settings),
            Button("Quit", "关闭当前客户端", self.quit),
        ]
        self.active = 0
        self.panel: str | None = None
        self.status = ""
        self.chat_messages: list[tuple[str, str]] = []
        self.chat_input = ""
        self.backend_status = "后端：未检测"
        self.sending = False
        self.background = self.load_background()

    def load_background(self) -> pygame.Surface | None:
        path = ASSETS / "resources" / "main-menu" / "background.png"
        if not path.exists():
            return None
        image = pygame.image.load(str(path)).convert()
        return pygame.transform.smoothscale(image, SCREEN_SIZE)

    def start(self) -> None:
        LOGGER.info("MainMenu.start selected")
        save_json(SAVE_PATH, {"startedAt": time.time(), "scene": "test"})
        self.app.set_scene(MapScene(self.app), "main menu start")

    def continue_game(self) -> None:
        if SAVE_PATH.exists():
            LOGGER.info("MainMenu.continue selected")
            self.app.set_scene(MapScene(self.app), "main menu continue")
        else:
            LOGGER.info("MainMenu.continue selected but no save exists")
            self.status = "暂无可读取的存档"

    def open_chat(self) -> None:
        self.panel = "chat"
        self.refresh_backend()

    def toggle_settings(self) -> None:
        self.panel = None if self.panel == "settings" else "settings"

    def quit(self) -> None:
        self.app.running = False

    def refresh_backend(self) -> None:
        self.backend_status = "后端：检测中"

        def worker() -> None:
            ok = llm_health(self.app.settings["serverUrl"])
            self.backend_status = "后端：已连接" if ok else "后端：未启动，先运行 npm run start:llm"

        threading.Thread(target=worker, daemon=True).start()

    def send_chat(self) -> None:
        text = self.chat_input.strip()
        if not text or self.sending:
            return
        self.chat_input = ""
        self.chat_messages.append(("你", text))
        self.chat_messages.append(("AI", "思考中..."))
        self.sending = True

        def worker() -> None:
            try:
                response = llm_generate(self.app.settings, self.chat_messages[:-1])
            except Exception as exc:  # noqa: BLE001 - user-facing status
                response = f"请求失败：{exc}"
            self.chat_messages[-1] = ("AI", response)
            self.sending = False

        threading.Thread(target=worker, daemon=True).start()

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            LOGGER.debug("MainMenu KEYDOWN key=%s panel=%s active=%s", pygame.key.name(event.key), self.panel, self.active)
            if self.panel == "chat":
                self.handle_chat_key(event)
                return
            if event.key in (pygame.K_UP, pygame.K_w):
                self.active = (self.active - 1) % len(self.buttons)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.active = (self.active + 1) % len(self.buttons)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.buttons[self.active].action()
            elif event.key == pygame.K_ESCAPE:
                self.panel = None
        elif event.type == pygame.MOUSEMOTION:
            for i, button in enumerate(self.buttons):
                if button.rect.collidepoint(event.pos):
                    self.active = i
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, button in enumerate(self.buttons):
                if button.rect.collidepoint(event.pos):
                    self.active = i
                    LOGGER.info("MainMenu mouse click button=%s pos=%s", button.label, event.pos)
                    button.action()
            if self.panel == "settings":
                self.settings_click(event.pos)
            elif self.panel == "chat":
                self.chat_click(event.pos)

    def handle_chat_key(self, event: pygame.event.Event) -> None:
        if event.key == pygame.K_ESCAPE:
            self.panel = None
        elif event.key == pygame.K_RETURN:
            self.send_chat()
        elif event.key == pygame.K_BACKSPACE:
            self.chat_input = self.chat_input[:-1]
        elif event.unicode and len(self.chat_input) < 500:
            self.chat_input += event.unicode

    def settings_click(self, pos: tuple[int, int]) -> None:
        if pygame.Rect(332, 238, 300, 42).collidepoint(pos):
            cycle_setting(self.app.settings, "providerId", PROVIDERS)
        elif pygame.Rect(332, 290, 300, 42).collidepoint(pos):
            cycle_setting(self.app.settings, "quality", QUALITIES)
        save_json(SETTINGS_PATH, self.app.settings)

    def chat_click(self, pos: tuple[int, int]) -> None:
        if pygame.Rect(650, 446, 86, 38).collidepoint(pos):
            self.send_chat()
        elif pygame.Rect(646, 202, 96, 32).collidepoint(pos):
            self.refresh_backend()
        elif pygame.Rect(534, 536, 90, 34).collidepoint(pos):
            self.panel = None

    def draw(self, surf: pygame.Surface) -> None:
        surf.fill(BG)
        if self.background:
            surf.blit(self.background, (0, 0))
        else:
            self.draw_fallback_background(surf)

        x, y = 56, 356
        for i, button in enumerate(self.buttons):
            button.rect.topleft = (x, y + i * 42)
            button.draw(surf, i == self.active)
        draw_text(surf, self.status, (114, 572), 14, (132, 118, 96))

        if self.panel == "settings":
            self.draw_settings(surf)
        elif self.panel == "chat":
            self.draw_chat(surf)

    def draw_fallback_background(self, surf: pygame.Surface) -> None:
        surf.fill((13, 20, 26))
        draw_text(surf, "AI Town", (70, 95), 58, TEXT, True)
        draw_text(surf, "Prototype build 0.1", (74, 166), 20, MUTED)
        pygame.draw.rect(surf, (48, 52, 50), (0, 468, 960, 94))
        for x in range(40, 920, 92):
            pygame.draw.rect(surf, (219, 184, 116), (x, 510, 42, 6))

    def draw_settings(self, surf: pygame.Surface) -> None:
        rect = pygame.Rect(300, 126, 360, 420)
        pygame.draw.rect(surf, PANEL, rect, border_radius=6)
        pygame.draw.rect(surf, (54, 58, 62), rect, 2, border_radius=6)
        draw_text(surf, "设置", (480, 172), 24, TEXT, True, True)
        rows = [
            ("LLM 服务", label_for(self.app.settings["providerId"], PROVIDERS), 238),
            ("模型档位", label_for(self.app.settings["quality"], QUALITIES), 290),
            ("后端地址", self.app.settings["serverUrl"].replace("http://", ""), 342),
            ("音量", "100%", 394),
        ]
        for name, value, top in rows:
            r = pygame.Rect(332, top, 300, 42)
            pygame.draw.rect(surf, PANEL_2, r, border_radius=5)
            pygame.draw.rect(surf, (82, 88, 92), r, 1, border_radius=5)
            draw_text(surf, name, (r.x + 14, r.y + 11), 16, MUTED)
            draw_text(surf, value, (r.right - 120, r.y + 11), 16, TEXT)
        draw_text(surf, "点击 LLM 服务或模型档位可切换", (347, 474), 14, (132, 118, 96))

    def draw_chat(self, surf: pygame.Surface) -> None:
        rect = pygame.Rect(180, 70, 600, 520)
        pygame.draw.rect(surf, PANEL, rect, border_radius=6)
        pygame.draw.rect(surf, (54, 58, 62), rect, 2, border_radius=6)
        draw_text(surf, "LLM 测试聊天", (230, 104), 24, TEXT, True)
        draw_text(surf, f"{label_for(self.app.settings['providerId'], PROVIDERS)} / {label_for(self.app.settings['quality'], QUALITIES)}", (532, 111), 15, MUTED)
        status_color = GOOD if "已连接" in self.backend_status else WARN
        draw_text(surf, self.backend_status, (226, 154), 15, status_color)
        self.small_button(surf, pygame.Rect(646, 146, 96, 32), "检测")

        log_rect = pygame.Rect(214, 194, 532, 270)
        pygame.draw.rect(surf, (22, 24, 26), log_rect, border_radius=5)
        pygame.draw.rect(surf, (54, 58, 62), log_rect, 1, border_radius=5)
        y = log_rect.y + 14
        for role, message in self.chat_messages[-8:]:
            color = (187, 217, 203) if role == "AI" else (239, 245, 233)
            for line in wrap_text(f"{role}: {message}", 488, 15):
                draw_text(surf, line, (log_rect.x + 16, y), 15, color)
                y += 22
                if y > log_rect.bottom - 22:
                    break
            y += 6
            if y > log_rect.bottom - 22:
                break

        input_rect = pygame.Rect(214, 486, 418, 42)
        pygame.draw.rect(surf, PANEL_2, input_rect, border_radius=5)
        pygame.draw.rect(surf, (82, 88, 92), input_rect, 1, border_radius=5)
        shown = self.chat_input if self.chat_input else "输入消息"
        draw_text(surf, shown[-48:], (input_rect.x + 14, input_rect.y + 11), 15, TEXT if self.chat_input else (120, 147, 142))
        self.small_button(surf, pygame.Rect(650, 488, 86, 38), "发送")
        self.small_button(surf, pygame.Rect(534, 536, 90, 34), "关闭")

    def small_button(self, surf: pygame.Surface, rect: pygame.Rect, label: str) -> None:
        pygame.draw.rect(surf, PANEL_2, rect, border_radius=5)
        pygame.draw.rect(surf, (82, 88, 92), rect, 1, border_radius=5)
        draw_text(surf, label, rect.center, 15, TEXT, center=True)
