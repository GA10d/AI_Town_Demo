from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from pathlib import Path

from .config import EMOTION_CATALOG_PATH


CSV_ENCODINGS = ("utf-8-sig", "utf-8", "gb18030", "cp936")


@dataclass(frozen=True)
class EmotionDefinition:
    id: str
    description: str


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
            emotion_id = (row.get("id") or "").strip()
            if not emotion_id or emotion_id.startswith("#"):
                continue
            rows.append({key: (value or "").strip() for key, value in row.items() if key})
        return rows
    if last_error:
        raise last_error
    return []


def load_emotion_catalog(path: Path = EMOTION_CATALOG_PATH) -> dict[str, EmotionDefinition]:
    catalog: dict[str, EmotionDefinition] = {}
    for row in csv_rows(path):
        emotion_id = row.get("id", "")
        catalog[emotion_id] = EmotionDefinition(
            id=emotion_id,
            description=row.get("description", ""),
        )
    return catalog


def emotion_catalog_prompt(catalog: dict[str, EmotionDefinition]) -> str:
    if not catalog:
        return "Emotion catalog: no known emotion ids are configured. Use neutral."
    lines = [
        "Emotion catalog available for the structured field emotion.",
        "Use neutral when there is no obvious emotion.",
        "Otherwise, use exactly one of these emotion ids:",
    ]
    for emotion_id in sorted(catalog):
        description = catalog[emotion_id].description or "(no description)"
        lines.append(f"- {emotion_id}: {description}")
    return "\n".join(lines)
