from __future__ import annotations

import json
import urllib.error
import urllib.request

from .config import PROVIDERS, QUALITIES


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
