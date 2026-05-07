from __future__ import annotations

import json
import threading

import pygame

from .config import MUTED, PANEL, PANEL_2, PROVIDERS, QUALITIES, SCREEN_SIZE, TEXT, WARN
from .graphics import draw_text, wrap_text
from .furniture import FurnitureDefinition, furniture_catalog_prompt
from .llm import label_for, llm_generate_json, llm_health
from .phone_schema import (
    display_text_from_structured,
    load_phone_response_schema,
    normalize_structured_response,
    structured_prompt,
)


class PhoneChatOverlay:
    def __init__(
        self,
        settings: dict,
        furniture_catalog: dict[str, FurnitureDefinition] | None = None,
    ):
        self.settings = settings
        self.furniture_catalog = furniture_catalog or {}
        self.is_open = False
        self.messages: list[tuple[str, str]] = []
        self.input_text = ""
        self.sending = False
        self.backend_ok: bool | None = None
        self.input_focused = False
        self.close_requested = False
        self.schema = load_phone_response_schema()
        self.system_prompt = "\n\n".join(
            [
                structured_prompt(self.schema),
                furniture_catalog_prompt(self.furniture_catalog),
            ]
        )
        self.structured_responses: list[dict] = []
        self.full_responses: list[dict] = []
        self.debug_open = False
        self.debug_scroll = 0
        self.rect = pygame.Rect(SCREEN_SIZE[0] - 344, SCREEN_SIZE[1] - 438, 328, 420)
        self.debug_rect = pygame.Rect(
            max(16, self.rect.x - 376),
            self.rect.y,
            360,
            self.rect.height,
        )
        self.close_button_rect = pygame.Rect(self.rect.right - 36, self.rect.y + 16, 22, 22)
        self.debug_button_rect = pygame.Rect(self.rect.right - 72, self.rect.y + 46, 54, 24)
        self.input_rect = pygame.Rect(0, 0, 0, 0)
        self.send_rect = pygame.Rect(0, 0, 64, 34)

    def open(self) -> None:
        self.is_open = True
        self.input_focused = True
        self.close_requested = False
        self.refresh_backend()

    def close(self) -> None:
        self.is_open = False
        self.debug_open = False
        self.debug_scroll = 0
        self.input_focused = False

    def toggle(self) -> bool:
        if self.is_open:
            self.close()
        else:
            self.open()
        return self.is_open

    def refresh_backend(self) -> None:
        self.backend_ok = None

        def worker() -> None:
            self.backend_ok = llm_health(self.settings["serverUrl"])

        threading.Thread(target=worker, daemon=True).start()

    def toggle_debug(self) -> None:
        self.debug_open = not self.debug_open
        self.debug_scroll = 0

    def consume_close_request(self) -> bool:
        requested = self.close_requested
        self.close_requested = False
        return requested

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.is_open:
            return False
        if event.type == pygame.TEXTINPUT:
            if not self.input_focused:
                return False
            if len(self.input_text) < 500:
                self.input_text += event.text
            return True
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN and self.input_focused:
                self.send()
            elif event.key == pygame.K_BACKSPACE and self.input_focused:
                self.input_text = self.input_text[:-1]
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.close_button_rect.collidepoint(event.pos):
                self.close_requested = True
                self.input_focused = False
                return True
            if self.debug_button_rect.collidepoint(event.pos):
                self.toggle_debug()
                self.input_focused = False
                return True
            if self.input_rect.collidepoint(event.pos):
                self.input_focused = True
                return True
            if self.send_rect.collidepoint(event.pos):
                self.send()
                self.input_focused = True
                return True
            if self.debug_open and self.debug_rect.collidepoint(event.pos):
                self.input_focused = False
                return True
            self.input_focused = False
            return self.rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEWHEEL:
            pos = pygame.mouse.get_pos()
            if self.debug_open and self.debug_rect.collidepoint(pos):
                self.debug_scroll = max(0, self.debug_scroll - event.y * 28)
                return True
            return self.rect.collidepoint(pos)
        if event.type in (pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
            pos = getattr(event, "pos", pygame.mouse.get_pos())
            return self.rect.collidepoint(pos) or (
                self.debug_open and self.debug_rect.collidepoint(pos)
            )
        return False

    def send(self) -> None:
        text = self.input_text.strip()
        if not text or self.sending:
            return
        self.input_text = ""
        self.messages.append(("You", text))
        self.messages.append(("AI", "Thinking..."))
        self.sending = True

        def worker() -> None:
            raw: dict | None = None
            structured: dict | None = None
            try:
                raw = llm_generate_json(
                    self.settings,
                    self.messages[:-1],
                    prompt_id=self.schema.get("prompt_id", "phone_chat"),
                    system_prompt=self.system_prompt,
                )
                self.full_responses.append(raw)
                structured = normalize_structured_response(raw, self.schema)
                response = display_text_from_structured(structured, self.schema) or str(structured)
            except Exception as exc:  # noqa: BLE001 - user-facing chat status
                response = f"Request failed: {exc}"
                if raw is None:
                    self.full_responses.append({"error": str(exc)})
                else:
                    self.full_responses[-1] = {"error": str(exc), "raw_response": raw}
            self.messages[-1] = ("AI", response)
            if structured is not None:
                self.structured_responses.append(structured)
            self.sending = False

        threading.Thread(target=worker, daemon=True).start()

    def draw(self, surf: pygame.Surface) -> None:
        if not self.is_open:
            return

        if self.debug_open:
            self.draw_debug_panel(surf)

        shadow = self.rect.move(4, 6)
        pygame.draw.rect(surf, (0, 0, 0), shadow, border_radius=8)
        pygame.draw.rect(surf, PANEL, self.rect, border_radius=8)
        pygame.draw.rect(surf, (72, 78, 82), self.rect, 2, border_radius=8)

        title_y = self.rect.y + 16
        draw_text(surf, "Phone", (self.rect.x + 18, title_y), 22, TEXT, True)
        provider = label_for(self.settings["providerId"], PROVIDERS)
        quality = label_for(self.settings["quality"], QUALITIES)
        draw_text(surf, f"{provider} / {quality}", (self.rect.x + 18, title_y + 30), 14, MUTED)
        self.draw_debug_button(surf)
        self.draw_close_button(surf)

        status = "checking" if self.backend_ok is None else ("online" if self.backend_ok else "offline")
        status_color = (132, 211, 151) if self.backend_ok else WARN
        draw_text(surf, status, (self.close_button_rect.x - 72, title_y + 3), 14, status_color)

        log_rect = pygame.Rect(self.rect.x + 16, self.rect.y + 76, self.rect.width - 32, 262)
        pygame.draw.rect(surf, (22, 24, 26), log_rect, border_radius=6)
        pygame.draw.rect(surf, (56, 60, 64), log_rect, 1, border_radius=6)
        self.draw_messages(surf, log_rect)

        self.input_rect = pygame.Rect(self.rect.x + 16, self.rect.bottom - 58, self.rect.width - 96, 36)
        self.send_rect = pygame.Rect(self.input_rect.right + 8, self.input_rect.y, 56, 36)
        pygame.draw.rect(surf, PANEL_2, self.input_rect, border_radius=6)
        border = (117, 150, 146) if self.input_focused else (86, 92, 98)
        pygame.draw.rect(surf, border, self.input_rect, 1, border_radius=6)
        shown = self.input_text if self.input_text else "Message"
        color = TEXT if self.input_text else (120, 132, 136)
        visible_text = shown[-32:]
        text_rect = draw_text(surf, visible_text, (self.input_rect.x + 10, self.input_rect.y + 9), 15, color)
        if self.input_focused and (pygame.time.get_ticks() // 500) % 2 == 0:
            text_end = text_rect.right + 2 if self.input_text else self.input_rect.x + 10
            caret_x = min(text_end, self.input_rect.right - 10)
            caret_top = self.input_rect.y + 9
            caret_bottom = self.input_rect.bottom - 9
            pygame.draw.line(surf, TEXT, (caret_x, caret_top), (caret_x, caret_bottom), 1)

        pygame.draw.rect(surf, (50, 72, 76), self.send_rect, border_radius=6)
        pygame.draw.rect(surf, (104, 134, 130), self.send_rect, 1, border_radius=6)
        draw_text(surf, "Send", self.send_rect.center, 14, TEXT, center=True)

    def draw_debug_button(self, surf: pygame.Surface) -> None:
        fill = (60, 82, 86) if self.debug_open else PANEL_2
        border = (117, 150, 146) if self.debug_open else (86, 92, 98)
        pygame.draw.rect(surf, fill, self.debug_button_rect, border_radius=5)
        pygame.draw.rect(surf, border, self.debug_button_rect, 1, border_radius=5)
        draw_text(surf, "JSON", self.debug_button_rect.center, 12, TEXT, center=True)

    def draw_close_button(self, surf: pygame.Surface) -> None:
        pygame.draw.rect(surf, (117, 35, 31), self.close_button_rect, border_radius=4)
        pygame.draw.rect(surf, (234, 89, 74), self.close_button_rect, 1, border_radius=4)
        x1 = self.close_button_rect.x + 6
        y1 = self.close_button_rect.y + 6
        x2 = self.close_button_rect.right - 6
        y2 = self.close_button_rect.bottom - 6
        pygame.draw.line(surf, TEXT, (x1, y1), (x2, y2), 2)
        pygame.draw.line(surf, TEXT, (x1, y2), (x2, y1), 2)

    def draw_messages(self, surf: pygame.Surface, rect: pygame.Rect) -> None:
        y = rect.y + 12
        for role, message in self.messages[-8:]:
            color = (187, 217, 203) if role == "AI" else (239, 245, 233)
            for line in wrap_text(f"{role}: {message}", rect.width - 26, 14):
                draw_text(surf, line, (rect.x + 12, y), 14, color)
                y += 20
                if y > rect.bottom - 18:
                    return
            y += 6
            if y > rect.bottom - 18:
                return

    def draw_debug_panel(self, surf: pygame.Surface) -> None:
        shadow = self.debug_rect.move(4, 6)
        pygame.draw.rect(surf, (0, 0, 0), shadow, border_radius=8)
        pygame.draw.rect(surf, PANEL, self.debug_rect, border_radius=8)
        pygame.draw.rect(surf, (72, 78, 82), self.debug_rect, 2, border_radius=8)

        draw_text(surf, "AI Full Response", (self.debug_rect.x + 16, self.debug_rect.y + 16), 20, TEXT, True)
        body_rect = pygame.Rect(
            self.debug_rect.x + 14,
            self.debug_rect.y + 54,
            self.debug_rect.width - 28,
            self.debug_rect.height - 72,
        )
        pygame.draw.rect(surf, (22, 24, 26), body_rect, border_radius=6)
        pygame.draw.rect(surf, (56, 60, 64), body_rect, 1, border_radius=6)

        content = self.full_responses[-1] if self.full_responses else {"status": "No AI response yet."}
        raw_text = json.dumps(content, ensure_ascii=False, indent=2)
        lines: list[str] = []
        for line in raw_text.splitlines():
            wrapped = wrap_text(line, body_rect.width - 24, 13)
            lines.extend(wrapped or [""])

        line_height = 18
        max_scroll = max(0, len(lines) * line_height - (body_rect.height - 20))
        self.debug_scroll = min(self.debug_scroll, max_scroll)

        previous_clip = surf.get_clip()
        surf.set_clip(body_rect.inflate(-4, -4))
        y = body_rect.y + 10 - self.debug_scroll
        for line in lines:
            if body_rect.y - line_height <= y <= body_rect.bottom:
                draw_text(surf, line, (body_rect.x + 12, y), 13, (201, 215, 211))
            y += line_height
        surf.set_clip(previous_clip)
