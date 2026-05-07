from __future__ import annotations

import csv
import io
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FURNITURE_DIR = ROOT / "assets" / "resources" / "furniture"
CATALOG_PATH = ROOT / "python_town" / "data" / "furniture_catalog.csv"
PLACEMENTS_PATH = ROOT / "python_town" / "data" / "furniture_placements.csv"
TILE_SIZE = 32
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
CSV_ENCODINGS = ("utf-8-sig", "utf-8", "gb18030", "cp936")
PLACEMENT_HEADER = ["id", "cell", "size", "access_tiles", "blocks_movement"]
DEFAULT_BLOCKS_MOVEMENT = "true"


def png_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as file:
        header = file.read(24)
    if len(header) < 24 or header[:8] != PNG_SIGNATURE or header[12:16] != b"IHDR":
        raise ValueError(f"Not a valid PNG file: {path}")
    return struct.unpack(">II", header[16:24])


def tile_size_for_png(path: Path) -> str:
    width, height = png_size(path)
    if width % TILE_SIZE or height % TILE_SIZE:
        raise ValueError(
            f"{path.name} is {width}x{height}; furniture PNGs must be multiples of {TILE_SIZE}px."
        )
    return f"{width // TILE_SIZE}x{height // TILE_SIZE}"


def existing_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    ids: set[str] = set()
    text, _encoding = read_csv_text(path)
    for row in csv.reader(io.StringIO(text)):
        if not row:
            continue
        furniture_id = row[0].strip()
        if not furniture_id or furniture_id == "id" or furniture_id.startswith("#"):
            continue
        ids.add(furniture_id)
    return ids


def read_csv_text(path: Path) -> tuple[str, str]:
    last_error: UnicodeDecodeError | None = None
    for encoding in CSV_ENCODINGS:
        try:
            return path.read_text(encoding=encoding), encoding
        except UnicodeDecodeError as exc:
            last_error = exc
    if last_error:
        raise last_error
    return "", "utf-8-sig"


def ensure_csv(path: Path, header: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or not read_csv_text(path)[0].strip():
        with path.open("w", encoding="utf-8-sig", newline="") as file:
            csv.writer(file).writerow(header)


def append_rows(path: Path, rows: list[list[str]]) -> None:
    if not rows:
        return
    text, encoding = read_csv_text(path) if path.exists() else ("", "utf-8-sig")
    with path.open("a", encoding=encoding, newline="") as file:
        if text and not text.endswith(("\n", "\r")):
            file.write("\n")
        writer = csv.writer(file)
        writer.writerows(rows)


def ensure_placement_blocks_column(path: Path) -> None:
    if not path.exists():
        return
    text, encoding = read_csv_text(path)
    if not text.strip():
        return
    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        return

    changed = False
    if "blocks_movement" not in rows[0]:
        rows[0].append("blocks_movement")
        changed = True
        print(f"Added blocks_movement column -> {path}")

    blocks_index = rows[0].index("blocks_movement")
    for row in rows[1:]:
        if not row:
            continue
        furniture_id = row[0].strip() if row else ""
        if not furniture_id or furniture_id.startswith("#"):
            continue
        while len(row) <= blocks_index:
            row.append("")
            changed = True
        if not row[blocks_index].strip():
            row[blocks_index] = DEFAULT_BLOCKS_MOVEMENT
            changed = True

    if not changed:
        return
    with path.open("w", encoding=encoding, newline="") as file:
        csv.writer(file).writerows(rows)


def main() -> int:
    if not FURNITURE_DIR.exists():
        print(f"Furniture image folder does not exist: {FURNITURE_DIR}")
        return 1

    ensure_csv(CATALOG_PATH, ["id", "description"])
    ensure_csv(PLACEMENTS_PATH, PLACEMENT_HEADER)
    ensure_placement_blocks_column(PLACEMENTS_PATH)

    catalog_ids = existing_ids(CATALOG_PATH)
    placement_ids = existing_ids(PLACEMENTS_PATH)
    catalog_rows: list[list[str]] = []
    placement_rows: list[list[str]] = []

    for png_path in sorted(FURNITURE_DIR.glob("*.png"), key=lambda path: path.name.casefold()):
        furniture_id = png_path.stem
        size = tile_size_for_png(png_path)
        if furniture_id not in catalog_ids:
            catalog_rows.append([furniture_id, ""])
            catalog_ids.add(furniture_id)
        if furniture_id not in placement_ids:
            placement_rows.append([furniture_id, "", size, "", DEFAULT_BLOCKS_MOVEMENT])
            placement_ids.add(furniture_id)

    append_rows(CATALOG_PATH, catalog_rows)
    append_rows(PLACEMENTS_PATH, placement_rows)

    print(f"Scanned: {FURNITURE_DIR}")
    print(f"Catalog rows added: {len(catalog_rows)} -> {CATALOG_PATH}")
    print(f"Placement rows added: {len(placement_rows)} -> {PLACEMENTS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
