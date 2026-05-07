from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import PHONE_RESPONSE_SCHEMA_PATH


def load_phone_response_schema(path: Path = PHONE_RESPONSE_SCHEMA_PATH) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if "fields" not in data or not isinstance(data["fields"], list):
        raise ValueError(f"Phone response schema must contain a fields list: {path}")
    return data


def structured_prompt(schema: dict[str, Any]) -> str:
    lines = [
        "Return a JSON object with exactly these configured fields.",
        "Use null for optional fields when there is no suitable value.",
        "Configured fields:",
    ]
    for field in schema["fields"]:
        name = field["name"]
        required = "required" if field.get("required") else "optional"
        field_type = field.get("type", "any")
        description = field.get("description", "")
        enum_values = field.get("enum")
        enum_text = f" Allowed values: {enum_values}." if enum_values else ""
        lines.append(f"- {name}: {field_type}, {required}. {description}{enum_text}")
    return "\n".join(lines)


def normalize_structured_response(data: Any, schema: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError("Structured phone response must be a JSON object.")
    normalized: dict[str, Any] = {}
    for field in schema["fields"]:
        name = field["name"]
        if name in data:
            value = data[name]
        elif field.get("required"):
            raise ValueError(f"Structured phone response missing required field: {name}")
        else:
            value = None
        enum_values = field.get("enum")
        if enum_values and value is not None and value not in enum_values:
            raise ValueError(
                f"Structured phone response field {name} must be one of {enum_values}, got {value!r}."
            )
        normalized[name] = value
    return normalized


def display_text_from_structured(data: dict[str, Any], schema: dict[str, Any]) -> str:
    display_field = schema.get("display_field", "reply")
    value = data.get(display_field)
    if value is None:
        return ""
    return str(value)
