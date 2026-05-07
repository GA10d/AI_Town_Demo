from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

from PIL import Image


@dataclass(frozen=True)
class SliceResult:
    output_path: Path
    row: int
    col: int
    source_index: int


def is_fully_transparent(image: Image.Image) -> bool:
    """Return True when every pixel has alpha 0."""
    if "A" not in image.getbands():
        return False
    return image.getchannel("A").getbbox() is None


def slice_png_tiles(
    input_path: str | Path,
    output_dir: str | Path,
    tile_width: int = 32,
    tile_height: int | None = None,
    start_index: int = 0,
    skip_transparent: bool = True,
    include_partial: bool = False,
    clean_output_pngs: bool = False,
    write_metadata: bool = True,
) -> list[SliceResult]:
    input_path = Path(input_path).expanduser().resolve()
    output_dir = Path(output_dir).expanduser().resolve()
    tile_height = tile_height or tile_width

    if tile_width <= 0 or tile_height <= 0:
        raise ValueError("tile_width and tile_height must be positive integers.")
    if not input_path.exists():
        raise FileNotFoundError(input_path)

    output_dir.mkdir(parents=True, exist_ok=True)
    if clean_output_pngs:
        for png in output_dir.glob("*.png"):
            png.unlink()

    source = Image.open(input_path).convert("RGBA")
    image_width, image_height = source.size
    cols = image_width // tile_width
    rows = image_height // tile_height
    if include_partial:
        cols += 1 if image_width % tile_width else 0
        rows += 1 if image_height % tile_height else 0

    results: list[SliceResult] = []
    output_index = start_index

    for row in range(rows):
        for col in range(cols):
            left = col * tile_width
            upper = row * tile_height
            right = min(left + tile_width, image_width)
            lower = min(upper + tile_height, image_height)

            if right <= left or lower <= upper:
                continue
            if not include_partial and (right - left != tile_width or lower - upper != tile_height):
                continue

            tile = source.crop((left, upper, right, lower))
            if tile.size != (tile_width, tile_height):
                padded = Image.new("RGBA", (tile_width, tile_height), (0, 0, 0, 0))
                padded.paste(tile, (0, 0))
                tile = padded

            if skip_transparent and is_fully_transparent(tile):
                continue

            output_path = output_dir / f"{output_index}.png"
            tile.save(output_path)
            results.append(
                SliceResult(
                    output_path=output_path,
                    row=row,
                    col=col,
                    source_index=row * cols + col,
                )
            )
            output_index += 1

    if write_metadata:
        metadata_path = output_dir / "tiles_metadata.csv"
        with metadata_path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["output_file", "row", "col", "source_index"])
            for result in results:
                writer.writerow([result.output_path.name, result.row, result.col, result.source_index])

    return results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Slice a PNG image into numbered PNG tiles.")
    parser.add_argument("input", help="Source PNG path.")
    parser.add_argument("output", help="Output directory.")
    parser.add_argument("--tile-size", type=int, default=32, help="Square tile size. Default: 32.")
    parser.add_argument("--tile-width", type=int, help="Tile width. Overrides --tile-size.")
    parser.add_argument("--tile-height", type=int, help="Tile height. Defaults to width.")
    parser.add_argument("--start-index", type=int, default=0, help="First output number. Default: 0.")
    parser.add_argument("--keep-transparent", action="store_true", help="Do not discard fully transparent tiles.")
    parser.add_argument("--include-partial", action="store_true", help="Include right/bottom edge partial tiles padded with transparency.")
    parser.add_argument("--clean-output-pngs", action="store_true", help="Delete existing PNGs in the output directory before slicing.")
    parser.add_argument("--no-metadata", action="store_true", help="Do not write tiles_metadata.csv.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    tile_width = args.tile_width or args.tile_size
    tile_height = args.tile_height or tile_width
    results = slice_png_tiles(
        input_path=args.input,
        output_dir=args.output,
        tile_width=tile_width,
        tile_height=tile_height,
        start_index=args.start_index,
        skip_transparent=not args.keep_transparent,
        include_partial=args.include_partial,
        clean_output_pngs=args.clean_output_pngs,
        write_metadata=not args.no_metadata,
    )
    print(f"Saved {len(results)} tiles to {Path(args.output).resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
