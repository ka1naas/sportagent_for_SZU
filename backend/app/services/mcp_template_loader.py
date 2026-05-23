import json
from pathlib import Path
from typing import Dict


class MCPTemplateManager:
    """
    负责加载与管理 MCP 训练规划模板资源。

    该类只依赖项目根目录下的 [`mcp_resources/templates/`](mcp_resources/templates) 静态 JSON 文件，
    不与具体路由、数据库或会话状态逻辑耦合，便于后续：
    - 作为 MCP 工具资源供外部智能体读取；
    - 由大模型直接消费；
    - 在未来替换为远程资源中心或版本化模板仓库。
    """

    GOAL_TO_TEMPLATE_FILE = {
        "减脂": "fat_loss.json",
        "增肌": "muscle_gain.json",
        "肌肥大": "muscle_gain.json",
        "爆发力": "power_agility.json",
        "弹跳": "power_agility.json",
        "耐力": "endurance.json",
        "马拉松": "endurance.json",
    }

    def __init__(self, template_dir: str = "mcp_resources/templates") -> None:
        self.template_dir = Path(template_dir)
        self.templates = self._load_templates()

    def _load_templates(self) -> Dict[str, dict]:
        if not self.template_dir.exists():
            raise FileNotFoundError(f"MCP 模板目录不存在: {self.template_dir}")

        loaded_templates = {}
        for template_file in self.template_dir.glob("*.json"):
            with template_file.open("r", encoding="utf-8") as file:
                loaded_templates[template_file.name] = json.load(file)

        return loaded_templates

    def get_template_by_goal(self, goal: str) -> dict:
        template_name = self.GOAL_TO_TEMPLATE_FILE.get(goal)
        if template_name is None:
            raise KeyError(f"未找到目标 `{goal}` 对应的 MCP 模板。")

        template_data = self.templates.get(template_name)
        if template_data is None:
            raise KeyError(f"模板文件 `{template_name}` 未成功加载。")

        return template_data


mcp_template_manager = MCPTemplateManager()
