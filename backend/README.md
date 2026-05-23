# Campus Fitness Scheduler Backend

## 痛点描述

校园健身规划往往存在三个典型问题：

1. **决策成本高**：学生需要自己在课程安排、训练目标、饮食预算之间来回权衡，很难快速形成可执行方案。
2. **信息割裂**：天气、场馆、食堂、个人时间等信息分散，缺少统一调度逻辑，计划容易流于理想化。
3. **计划抗干扰能力弱**：一旦遇到天气变化、场馆条件变化或用户反馈，传统计划往往难以及时修正。

本项目围绕“零决策成本、低经济成本、抗天气干扰”的校园场景，构建一个可组合、可扩展的智能健身调度后端。系统通过固定问卷采集边界条件，再结合天气、饮食、训练模板与 LLM 生成能力，输出更贴近校园现实条件的健身与饮食计划。

---

## 新增功能清单

当前代码主干已经围绕统一架构完成收口，并具备以下核心能力：

### 1. 五步问卷式边界条件采集

- 由 [`BoundaryCollectorService`](backend/app/subsystems/boundary_collector/collector_service.py:13) 负责管理问卷状态流转；
- 将用户的 `session_id`、当前步骤与问卷载荷统一持久化；
- 输出标准化边界条件模型 [`UserBoundaryConditions`](backend/app/models/schemas.py:38)。

### 2. 统一的健身计划编排主干

- 核心编排位于 [`backend/app/orchestrators/fitness_workflow.py`](backend/app/orchestrators/fitness_workflow.py:1)；
- 统一串联天气评估、饮食推荐、训练模板选择与计划生成；
- 支持计划生成、修正、接受等动作处理。

### 3. 三大领域能力模块

- 饮食领域：[`calculate_macro_targets()`](backend/app/domains/diet_domain.py:46)、[`generate_diet_plan()`](backend/app/domains/diet_domain.py:67)
- 训练领域：[`load_exercise_templates()`](backend/app/domains/exercise_domain.py:21)、[`select_exercise_template()`](backend/app/domains/exercise_domain.py:32)
- 天气领域：[`fetch_weather_snapshot()`](backend/app/domains/weather_domain.py:46)、[`evaluate_weather_venues()`](backend/app/domains/weather_domain.py:83)

### 4. Prompt 聚合与 LLM 生成解耦

- [`FitnessPromptAggregator`](backend/app/core/prompt_aggregator.py:10) 负责聚合用户边界条件、天气结果、饮食建议与训练模板；
- [`LLMAdapter`](backend/app/adapters/llm_adapter.py:11) 专注模型调用，兼容 OpenAI 协议服务；
- 便于后续替换不同模型供应商或本地模型服务。

### 5. 状态与计划历史持久化

- 应用启动时在 [`on_startup()`](backend/main.py:29) 中触发 [`init_db()`](db/database.py:32) 初始化数据库；
- 数据访问基于 [`get_db()`](db/database.py:24) 提供的 SQLAlchemy Session；
- 问卷状态与计划历史统一由 [`db/models.py`](db/models.py:1) 中的模型维护。

### 6. FastAPI API 能力

- 应用入口位于 [`backend/main.py`](backend/main.py:1)；
- 路由统一汇总于 [`api_router`](backend/app/routers/__init__.py:11)；
- 当前已包含聊天问卷、计划生成、用户资料与天气能力相关接口。

### 7. 前端联调基础能力

- 前端基于 Next.js 15，脚本定义见 [`frontend/package.json`](frontend/package.json:1)；
- 已提供计划页、规划页及配套 API Client，可与后端联调运行。

---

## 运行说明

### 1. 环境要求

- Python 3.10+
- Node.js 18+
- npm

后端依赖定义见 [`backend/requirements.txt`](backend/requirements.txt:1)，前端依赖与脚本定义见 [`frontend/package.json`](frontend/package.json:1)。

### 2. 启动后端

在项目根目录执行：

```bash
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload
```

后端默认入口为：

- 应用根路径：`http://127.0.0.1:8000/`
- Swagger 文档：`http://127.0.0.1:8000/docs`

其中 FastAPI 应用定义于 [`app = FastAPI(...)`](backend/main.py:9)。

### 3. 启动前端

在 [`frontend/`](frontend/) 目录执行：

```bash
npm install
npm run dev
```

前端开发服务默认运行在 `http://127.0.0.1:3000/`。

### 4. 数据库初始化

后端启动时会自动调用 [`init_db()`](db/database.py:32) 完成数据库初始化，因此通常无需单独执行额外建表命令。

### 5. 基础检查

如需快速验证后端导入与语法状态，可在项目根目录执行：

```bash
python -m compileall ./backend ./db ./tests
python -c "from backend.main import app; print(app.title)"
```

---

## 项目结构概览

- 后端入口：[`backend/main.py`](backend/main.py:1)
- 编排层：[`backend/app/orchestrators/fitness_workflow.py`](backend/app/orchestrators/fitness_workflow.py:1)
- 边界采集子系统：[`backend/app/subsystems/boundary_collector/collector_service.py`](backend/app/subsystems/boundary_collector/collector_service.py:1)
- 领域模块：[`backend/app/domains/`](backend/app/domains/)
- Prompt 聚合：[`backend/app/core/prompt_aggregator.py`](backend/app/core/prompt_aggregator.py:1)
- 模型适配层：[`backend/app/adapters/llm_adapter.py`](backend/app/adapters/llm_adapter.py:1)
- 数据持久化：[`db/`](db/)
- 前端应用：[`frontend/`](frontend/)
