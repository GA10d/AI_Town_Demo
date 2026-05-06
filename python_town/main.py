from __future__ import annotations

import csv
import json
import math
import sys
import threading
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pygame


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
SETTINGS_PATH = ROOT / "python_town" / "settings.json"
SAVE_PATH = ROOT / "python_town" / "save.json"

SCREEN_SIZE = (960, 640)
BG = (7, 8, 8)
PANEL = (18, 20, 22)
PANEL_2 = (30, 33, 36)
TEXT = (236, 238, 240)
MUTED = (151, 174, 166)
ACCENT = (236, 174, 88)
GOOD = (132, 211, 151)
WARN = (236, 174, 88)

PROVIDERS = [
    ("chatgpt", "ChatGPT"),
    ("deepseek", "DeepSeek"),
    ("gemini", "Gemini"),
    ("doubao", "Doubao"),
    ("qwen", "Qwen"),
    ("custom-openai-compatible", "Custom"),
]
QUALITIES = [("fast", "Fast"), ("standard", "Standard")]


def load_json(path: Path, defaults: dict) -> dict:
    if not path.exists():
        return dict(defaults)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return dict(defaults)
    return {**defaults, **data}


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def font(size: int, bold: bool = False) -> pygame.font.Font:
    names = ["Microsoft YaHei UI", "Microsoft YaHei", "SimHei", "Arial"]
    return pygame.font.SysFont(names, size, bold=bold)


def draw_text(
    surf: pygame.Surface,
    text: str,
    pos: tuple[int, int],
    size: int = 18,
    color: tuple[int, int, int] = TEXT,
    bold: bool = False,
    center: bool = False,
) -> pygame.Rect:
    image = font(size, bold).render(text, True, color)
    rect = image.get_rect()
    rect.center = pos if center else rect.center
    if not center:
        rect.topleft = pos
    surf.blit(image, rect)
    return rect


def wrap_text(text: str, max_width: int, size: int) -> list[str]:
    f = font(size)
    lines: list[str] = []
    for raw in text.splitlines() or [""]:
        current = ""
        tokens = list(raw) if any(ord(ch) > 127 for ch in raw) else raw.split(" ")
        sep = "" if any(ord(ch) > 127 for ch in raw) else " "
        for token in tokens:
            trial = token if not current else current + sep + token
            if f.size(trial)[0] <= max_width:
                current = trial
            else:
                if current:
                    lines.append(current)
                current = token
        lines.append(current)
    return lines


@dataclass
class Tileset:
    firstgid: int
    name: str
    tile_width: int
    tile_height: int
    tile_count: int
    columns: int
    image_path: Path
    image: pygame.Surface

    @property
    def lastgid(self) -> int:
        return self.firstgid + self.tile_count - 1

    def tile_rect(self, gid: int) -> pygame.Rect:
        local_id = gid - self.firstgid
        x = (local_id % self.columns) * self.tile_width
        y = (local_id // self.columns) * self.tile_height
        return pygame.Rect(x, y, self.tile_width, self.tile_height)


@dataclass
class TileLayer:
    name: str
    width: int
    height: int
    gids: list[int]


@dataclass
class TileMap:
    width: int
    height: int
    tile_width: int
    tile_height: int
    tilesets: list[Tileset]
    layers: list[TileLayer]

    @property
    def pixel_size(self) -> tuple[int, int]:
        return self.width * self.tile_width, self.height * self.tile_height

    def tileset_for_gid(self, gid: int) -> Tileset | None:
        for tileset in reversed(self.tilesets):
            if gid >= tileset.firstgid:
                return tileset
        return None


def parse_tilemap(tmx_path: Path) -> TileMap:
    root = ET.parse(tmx_path).getroot()
    tilesets: list[Tileset] = []
    for elem in root.findall("tileset"):
        firstgid = int(elem.attrib["firstgid"])
        tsx_path = (tmx_path.parent / elem.attrib["source"]).resolve()
        tsx = ET.parse(tsx_path).getroot()
        image_elem = tsx.find("image")
        if image_elem is None:
            raise ValueError(f"Tileset has no image: {tsx_path}")
        image_path = (tsx_path.parent / image_elem.attrib["source"]).resolve()
        if not image_path.exists():
            alt = ASSETS / "tiles" / "images" / image_path.name
            image_path = alt if alt.exists() else image_path
        image = pygame.image.load(str(image_path)).convert_alpha()
        tilesets.append(
            Tileset(
                firstgid=firstgid,
                name=tsx.attrib["name"],
                tile_width=int(tsx.attrib["tilewidth"]),
                tile_height=int(tsx.attrib["tileheight"]),
                tile_count=int(tsx.attrib["tilecount"]),
                columns=int(tsx.attrib["columns"]),
                image_path=image_path,
                image=image,
            )
        )

    layers: list[TileLayer] = []
    for elem in root.findall("layer"):
        data = elem.find("data")
        if data is None or data.attrib.get("encoding") != "csv":
            raise ValueError("Only CSV encoded TMX layers are supported.")
        gids: list[int] = []
        for row in csv.reader((data.text or "").strip().splitlines()):
            gids.extend(int(cell) for cell in row if cell.strip())
        layers.append(TileLayer(elem.attrib["name"], int(elem.attrib["width"]), int(elem.attrib["height"]), gids))

    return TileMap(
        width=int(root.attrib["width"]),
        height=int(root.attrib["height"]),
        tile_width=int(root.attrib["tilewidth"]),
        tile_height=int(root.attrib["tileheight"]),
        tilesets=tilesets,
        layers=layers,
    )


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
        save_json(SAVE_PATH, {"startedAt": time.time(), "scene": "test"})
        self.app.scene = MapScene(self.app)

    def continue_game(self) -> None:
        if SAVE_PATH.exists():
            self.app.scene = MapScene(self.app)
        else:
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


class MapScene:
    def __init__(self, app: "App"):
        self.app = app
        self.tilemap = parse_tilemap(ASSETS / "tilemap" / "map_test.tmx")
        self.player = pygame.Vector2(6, 5)
        self.scale = 2
        self.message = "Esc 返回主菜单  |  WASD/方向键移动"

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_ESCAPE:
            self.app.scene = self.app.menu
            return
        delta = pygame.Vector2(0, 0)
        if event.key in (pygame.K_LEFT, pygame.K_a):
            delta.x = -1
        elif event.key in (pygame.K_RIGHT, pygame.K_d):
            delta.x = 1
        elif event.key in (pygame.K_UP, pygame.K_w):
            delta.y = -1
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            delta.y = 1
        if delta.length_squared():
            target = self.player + delta
            if 0 <= target.x < self.tilemap.width and 0 <= target.y < self.tilemap.height:
                self.player = target
                save_json(SAVE_PATH, {"scene": "test", "player": [int(self.player.x), int(self.player.y)], "savedAt": time.time()})

    def draw(self, surf: pygame.Surface) -> None:
        surf.fill((11, 13, 14))
        map_w, map_h = self.tilemap.pixel_size
        tw = self.tilemap.tile_width * self.scale
        th = self.tilemap.tile_height * self.scale
        ox = (SCREEN_SIZE[0] - map_w * self.scale) // 2
        oy = (SCREEN_SIZE[1] - map_h * self.scale) // 2 - 20
        pygame.draw.rect(surf, (18, 20, 22), (ox - 24, oy - 24, map_w * self.scale + 48, map_h * self.scale + 48), border_radius=6)
        pygame.draw.rect(surf, (54, 58, 62), (ox - 24, oy - 24, map_w * self.scale + 48, map_h * self.scale + 48), 2, border_radius=6)

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
                if self.scale != 1:
                    tile = pygame.transform.scale(tile, (tw, th))
                surf.blit(tile, (ox + x * tw, oy + y * th))

        px = ox + int(self.player.x) * tw + tw // 2
        py = oy + int(self.player.y) * th + th // 2
        pygame.draw.circle(surf, (67, 176, 218), (px, py), 17)
        pygame.draw.circle(surf, (240, 250, 255), (px, py - 4), 8)
        pygame.draw.circle(surf, (10, 20, 26), (px - 3, py - 6), 2)
        pygame.draw.circle(surf, (10, 20, 26), (px + 4, py - 6), 2)

        draw_text(surf, "AI Town / test.scene", (32, 28), 24, TEXT, True)
        draw_text(surf, f"TMX: {self.tilemap.width}x{self.tilemap.height}, layers: {', '.join(layer.name for layer in self.tilemap.layers)}", (32, 62), 15, MUTED)
        draw_text(surf, self.message, (32, 596), 16, (132, 118, 96))


class App:
    def __init__(self):
        pygame.init()
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

    def run(self) -> None:
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                else:
                    self.scene.handle_event(event)
            self.scene.draw(self.screen)
            pygame.display.flip()
            self.clock.tick(60)
        pygame.quit()


def label_for(value: str, options: list[tuple[str, str]]) -> str:
    return next((label for key, label in options if key == value), options[0][1])


def cycle_setting(settings: dict, key: str, options: list[tuple[str, str]]) -> None:
    values = [value for value, _ in options]
    idx = values.index(settings.get(key, values[0])) if settings.get(key, values[0]) in values else 0
    settings[key] = values[(idx + 1) % len(values)]


def llm_health(server_url: str) -> bool:
    try:
        with urllib.request.urlopen(f"{server_url.rstrip('/')}/api/health", timeout=2.5) as response:
            return 200 <= response.status < 300
    except (OSError, urllib.error.URLError):
        return False


def llm_generate(settings: dict, messages: list[tuple[str, str]]) -> str:
    payload = {
        "promptId": "llm_test",
        "profileId": settings["providerId"],
        "quality": settings["quality"],
        "messages": [
            {"role": "assistant" if role == "AI" else "user", "content": text}
            for role, text in messages[-8:]
        ],
    }
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{settings['serverUrl'].rstrip('/')}/api/llm/generate",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(body or f"LLM request failed: {exc.code}") from exc
    return result.get("text") or "(空回复)"


if __name__ == "__main__":
    try:
        App().run()
    except Exception as exc:  # noqa: BLE001
        pygame.quit()
        print(f"AI Town Python crashed: {exc}", file=sys.stderr)
        raise
