from __future__ import annotations

import csv
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

import pygame

from .config import ASSETS


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

    def gid_at(self, x: int, y: int) -> int:
        if x < 0 or y < 0 or x >= self.width or y >= self.height:
            return 0
        return self.gids[y * self.width + x]


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

    def layer_named(self, name: str) -> TileLayer | None:
        return next((layer for layer in self.layers if layer.name == name), None)


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

