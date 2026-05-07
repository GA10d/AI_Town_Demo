from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from pathlib import Path

import pygame

from .config import FURNITURE_IMAGE_DIRS
from .logging_config import LOGGER


CSV_ENCODINGS = ("utf-8-sig", "utf-8", "gb18030", "cp936")


@dataclass(frozen=True)
class FurnitureDefinition:
    id: str
    description: str


@dataclass(frozen=True)
class FurniturePlacement:
    id: str
    cell: tuple[int, int]
    size: tuple[int, int]
    access_tiles: tuple[tuple[int, int], ...]
    blocks_movement: bool

    @property
    def covered_cells(self) -> tuple[tuple[int, int], ...]:
        x, bottom_y = self.cell
        width, height = self.size
        return tuple((x + dx, bottom_y - dy) for dx in range(width) for dy in range(height))


def parse_grid_cell(value: str, field_name: str) -> tuple[int, int]:
    match = re.search(r"\(?\s*(-?\d+)\s*[,:\s]\s*(-?\d+)\s*\)?", value.strip())
    if not match:
        raise ValueError(f"Invalid {field_name}: {value!r}. Use '(x,y)' or 'x:y'.")
    return int(match.group(1)), int(match.group(2))


def parse_grid_cell_list(value: str) -> tuple[tuple[int, int], ...]:
    text = value.strip()
    if not text:
        return tuple()
    matches = re.findall(r"\(?\s*(-?\d+)\s*[,:\s]\s*(-?\d+)\s*\)?", text)
    if not matches:
        raise ValueError(f"Invalid access_tiles: {value!r}. Use '(x,y);(x,y)' or 'x:y|x:y'.")
    return tuple((int(x), int(y)) for x, y in matches)


def parse_grid_size(value: str) -> tuple[int, int]:
    match = re.search(r"^\s*(\d+)\s*[xX*]\s*(\d+)\s*$", value.strip())
    if not match:
        raise ValueError(f"Invalid furniture size: {value!r}. Use 'widthxheight', for example '1x2'.")
    width, height = int(match.group(1)), int(match.group(2))
    if width <= 0 or height <= 0:
        raise ValueError(f"Furniture size must be positive: {value!r}")
    return width, height


def parse_bool(value: str, default: bool = True) -> bool:
    text = value.strip().lower()
    if not text:
        return default
    if text in ("true", "t", "yes", "y", "1"):
        return True
    if text in ("false", "f", "no", "n", "0"):
        return False
    raise ValueError(f"Invalid boolean value: {value!r}. Use true or false.")


def csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    last_error: UnicodeDecodeError | None = None
    for encoding in CSV_ENCODINGS:
        try:
            text = path.read_text(encoding=encoding)
        except UnicodeDecodeError as exc:
            last_error = exc
            continue
        rows: list[dict[str, str]] = []
        for row in csv.DictReader(io.StringIO(text)):
            furniture_id = (row.get("id") or "").strip()
            if not furniture_id or furniture_id.startswith("#"):
                continue
            rows.append({key: (value or "").strip() for key, value in row.items() if key})
        if encoding not in ("utf-8-sig", "utf-8"):
            LOGGER.info("Loaded furniture CSV with %s encoding: %s", encoding, path)
        return rows
    if last_error:
        raise last_error
    return []


def load_furniture_catalog(path: Path) -> dict[str, FurnitureDefinition]:
    catalog: dict[str, FurnitureDefinition] = {}
    for row in csv_rows(path):
        furniture_id = row.get("id", "")
        catalog[furniture_id] = FurnitureDefinition(
            id=furniture_id,
            description=row.get("description", ""),
        )
    return catalog


def load_furniture_placements(path: Path, catalog: dict[str, FurnitureDefinition]) -> list[FurniturePlacement]:
    placements: list[FurniturePlacement] = []
    for row in csv_rows(path):
        furniture_id = row.get("id", "")
        if catalog and furniture_id not in catalog:
            LOGGER.warning("Furniture placement references id not in catalog: %s", furniture_id)
        placements.append(
            FurniturePlacement(
                id=furniture_id,
                cell=parse_grid_cell(row.get("cell", ""), "cell"),
                size=parse_grid_size(row.get("size", "1x1")),
                access_tiles=parse_grid_cell_list(row.get("access_tiles", "")),
                blocks_movement=parse_bool(row.get("blocks_movement", ""), True),
            )
        )
    return placements


def load_furniture_image(furniture_id: str) -> pygame.Surface | None:
    for directory in FURNITURE_IMAGE_DIRS:
        path = directory / f"{furniture_id}.png"
        if path.exists():
            return pygame.image.load(str(path)).convert_alpha()
    return None
