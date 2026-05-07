from __future__ import annotations

import csv
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
EMOTION_DIR = REPO_ROOT / "assets" / "resources" / "emotion"
OUTPUT_PATH = REPO_ROOT / "python_town" / "data" / "emotion_catalog.csv"

DESCRIPTIONS = {
    "knife": "带有小刀图标的对话气泡，表示敌意、攻击性或想要伤害别人的危险情绪。",
    "like": "带有红色爱心的对话气泡，表示喜欢、认可、亲近或对某人某事产生好感。",
    "mad": "带有愤怒表情的对话气泡，表示生气、恼火、被冒犯或情绪失控。",
    "money": "带有金钱符号的对话气泡，表示关心金钱、交易、奖励或利益相关的想法。",
    "quetion": "带有问号的对话气泡，表示疑惑、不理解、正在思考或需要进一步询问。",
    "sad": "带有伤心爱心的对话气泡，表示难过、失落、委屈或情感受伤。",
    "shock": "带有感叹号的对话气泡，表示惊讶、震惊、突然意识到问题或受到刺激。",
    "shy": "带有粉色斜线的对话气泡，表示害羞、尴尬、脸红或不好意思表达。",
    "sleepy": "带有睡眠符号的对话气泡，表示困倦、疲惫、想休息或注意力下降。",
    "water": "带有水滴的对话气泡，表示口渴、流汗、紧张出汗或需要水相关的需求。",
}


def collect_emotions() -> list[tuple[str, str]]:
    rows = []
    for png_path in sorted(EMOTION_DIR.glob("*.png")):
        emotion_id = png_path.stem
        try:
            description = DESCRIPTIONS[emotion_id]
        except KeyError as exc:
            raise KeyError(f"Missing Chinese description for {png_path.name}") from exc
        rows.append((emotion_id, description))
    return rows


def write_csv(rows: list[tuple[str, str]]) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["id", "description"])
        writer.writerows(rows)


def main() -> None:
    write_csv(collect_emotions())
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
