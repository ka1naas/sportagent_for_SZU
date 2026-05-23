from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.app.domains.schemas import ExerciseTemplateOutput


GOAL_TO_TEMPLATE_FILE = {
    "减脂": "fat_loss.json",
    "增肌": "muscle_gain.json",
    "肌肥大": "muscle_gain.json",
    "力量": "power_agility.json",
    "爆发力": "power_agility.json",
    "弹跳": "power_agility.json",
    "耐力": "endurance.json",
    "马拉松": "endurance.json",
}


def load_exercise_templates(template_dir: str = "mcp_resources/templates") -> dict[str, dict[str, Any]]:
    template_path = Path(template_dir)
    if not template_path.exists():
        raise FileNotFoundError(f"MCP 模板目录不存在: {template_path}")
    loaded_templates: dict[str, dict[str, Any]] = {}
    for template_file in template_path.glob("*.json"):
        with template_file.open("r", encoding="utf-8") as file:
            loaded_templates[template_file.name] = json.load(file)
    return loaded_templates


def select_exercise_template(*, goal: str, templates: dict[str, dict[str, Any]]) -> ExerciseTemplateOutput:
    template_name = GOAL_TO_TEMPLATE_FILE.get(goal)
    if template_name is None:
        raise KeyError(f"未找到目标 `{goal}` 对应的 MCP 模板。")
    template_data = templates.get(template_name)
    if template_data is None:
        raise KeyError(f"模板文件 `{template_name}` 未成功加载。")
    return ExerciseTemplateOutput(goal=goal, template_name=template_name, template_data=template_data)
