# Campus Fitness Scheduler Backend

## 1. 当前项目状态

该项目已经完成从“新旧架构并存”向统一架构的收敛，当前主干全部落在 [`backend/app/`](backend/app/) 下。

当前系统采用以下固定结构：

1. 编排层：[`backend/app/orchestrators/fitness_workflow.py`](backend/app/orchestrators/fitness_workflow.py:1)
2. 边界条件采集子系统：[`BoundaryCollectorService`](backend/app/subsystems/boundary_collector/collector_service.py:13)
3. 三个领域模块：
   - 饮食：[`backend/app/domains/diet_domain.py`](backend/app/domains/diet_domain.py:1)
   - 训练：[`backend/app/domains/exercise_domain.py`](backend/app/domains/exercise_domain.py:1)
   - 天气：[`backend/app/domains/weather_domain.py`](backend/app/domains/weather_domain.py:1)
4. Prompt 聚合器：[`FitnessPromptAggregator`](backend/app/core/prompt_aggregator.py:10)
5. LLM 适配器：[`LLMAdapter`](backend/app/adapters/llm_adapter.py:11)

---

## 2. 目录结构

```text
backend/
├── main.py
├── README.md
├── rebuild.md
├── app/
│   ├── adapters/
│   │   ├── __init__.py
│   │   └── llm_adapter.py
│   ├── core/
│   │   ├── __init__.py
│   │   └── prompt_aggregator.py
│   ├── domains/
│   │   ├── __init__.py
│   │   ├── diet_domain.py
│   │   ├── exercise_domain.py
│   │   ├── schemas.py
│   │   └── weather_domain.py
│   ├── models/
│   ├── orchestrators/
│   │   ├── __init__.py
│   │   └── fitness_workflow.py
│   ├── routers/
│   ├── services/
│   │   ├── __init__.py
│   │   └── mcp_template_loader.py
│   ├── subsystems/
│   │   ├── __init__.py
│   │   └── boundary_collector/
│   │       ├── __init__.py
│   │       └── collector_service.py
│   └── utils/
├── config/
└── data/

db/
├── __init__.py
├── database.py
└── models.py
```

说明：

- 原 [`new_arch/`](new_arch/) 已被收口进 [`backend/app/`](backend/app/)；
- 旧的重复 `service` 文件已经移除；
- 目前 [`backend/app/services/`](backend/app/services/) 仅保留仍有意义的模板加载器 [`MCPTemplateManager`](backend/app/services/mcp_template_loader.py:6)。

---

## 3. 架构说明

### 3.1 API / 路由层

对外入口仍然通过 FastAPI 暴露：

- 入口应用：[`backend/main.py`](backend/main.py:1)
- 路由汇总：[`api_router`](backend/app/routers/__init__.py:11)

当前路由职责被限制为：

- 接收 HTTP 请求；
- 参数校验；
- 调用编排层或子系统；
- 返回响应。

主要接口：

- 五步问卷：[`backend/app/routers/chat.py`](backend/app/routers/chat.py:1)
- 计划生成 / 修正 / 接受：[`backend/app/routers/plan_routes.py`](backend/app/routers/plan_routes.py:1)
- 用户资料持久化：[`backend/app/routers/user_routes.py`](backend/app/routers/user_routes.py:1)
- 天气适宜度：[`backend/app/routers/weather_routes.py`](backend/app/routers/weather_routes.py:1)

### 3.2 编排层

唯一业务主干为 [`backend/app/orchestrators/fitness_workflow.py`](backend/app/orchestrators/fitness_workflow.py:1)。

它负责：

- 拉取边界条件；
- 调用天气 / 饮食 / 训练三个领域模块；
- 调用 [`FitnessPromptAggregator`](backend/app/core/prompt_aggregator.py:10) 组装 Prompt；
- 调用 [`LLMAdapter`](backend/app/adapters/llm_adapter.py:11) 生成文本；
- 持久化计划历史；
- 处理生成、修正、接受三个动作。

### 3.3 边界条件采集子系统

唯一状态源为 [`BoundaryCollectorService`](backend/app/subsystems/boundary_collector/collector_service.py:13)。

其职责：

- 维护五步问卷状态流转；
- 持久化 `session_id / current_step / payload`；
- 输出标准化边界条件结构 [`UserBoundaryConditions`](backend/app/models/schemas.py:38)。

### 3.4 Domain 层

三个领域模块已经收口为唯一实现：

- 饮食：[`calculate_macro_targets()`](backend/app/domains/diet_domain.py:46)、[`generate_diet_plan()`](backend/app/domains/diet_domain.py:67)
- 训练：[`load_exercise_templates()`](backend/app/domains/exercise_domain.py:21)、[`select_exercise_template()`](backend/app/domains/exercise_domain.py:32)
- 天气：[`fetch_weather_snapshot()`](backend/app/domains/weather_domain.py:46)、[`evaluate_weather_venues()`](backend/app/domains/weather_domain.py:83)

### 3.5 Prompt 聚合器

[`FitnessPromptAggregator`](backend/app/core/prompt_aggregator.py:10) 只负责组装：

- 用户边界条件
- 天气评估结果
- 饮食推荐
- 训练模板

它不再承担宏量计算、食堂筛选、天气抓取等业务动作。

### 3.6 LLM 适配器

[`LLMAdapter`](backend/app/adapters/llm_adapter.py:11) 是纯模型调用层，只负责：

- 接收 `messages`
- 调用兼容 OpenAI 协议的模型服务
- 返回文本输出

### 3.7 持久化层

当前全部业务状态统一通过 SQLAlchemy 管理：

- DB Session：[`get_db()`](db/database.py:24)
- 初始化：[`init_db()`](db/database.py:32)
- 核心模型：[`db/models.py`](db/models.py:1)

其中新增并使用了：

- [`BoundarySession`](db/models.py:58)
- [`PlanHistory`](db/models.py:67)

---

## 4. 本轮重构完成内容

### 4.1 已消除的旧状态管理问题

- 移除了内存态计划缓存 [`PLAN_STORE`](backend/app/routers/plan_routes.py:21) 的旧方案；
- 移除了编排层内存态历史缓存 `_PLAN_HISTORY_STORE` 的旧方案；
- 计划草案和对话历史已统一持久化到 [`PlanHistory`](db/models.py:67)。

### 4.2 已消除的双状态源问题

- 原生 SQLite 版 [`ChatSessionService`](backend/app/services/chat_session_service.py:11) 已废弃；
- 统一收口为 [`BoundaryCollectorService`](backend/app/subsystems/boundary_collector/collector_service.py:13)；
- 五步问卷状态改为通过 SQLAlchemy 模型 [`BoundarySession`](db/models.py:58) 管理。

### 4.3 已消除的重复领域实现

以下旧文件已移除：

- [`backend/app/services/weather_service.py`](backend/app/services/weather_service.py)
- [`backend/app/services/venue_analyzer.py`](backend/app/services/venue_analyzer.py)
- [`backend/app/services/nutrition_calc.py`](backend/app/services/nutrition_calc.py)
- [`backend/app/services/diet_planner.py`](backend/app/services/diet_planner.py)
- [`backend/app/services/llm_service.py`](backend/app/services/llm_service.py)
- [`backend/app/services/dispatch_engine.py`](backend/app/services/dispatch_engine.py)
- [`backend/app/services/chat_session_service.py`](backend/app/services/chat_session_service.py)

### 4.4 已完成的目录收口

- 将原 [`new_arch/`](new_arch/) 中的适配器、聚合器、领域模块、编排层、边界采集子系统迁移到 [`backend/app/`](backend/app/) 统一结构下；
- 删除了所有残留的 [`new_arch/`](new_arch/) Python 实现文件；
- 代码仓库不再存在“一半旧架构、一半新架构”的导入路径。

---

## 5. 当前是否符合目标架构

结论：**是，当前代码结构已经符合 [`backend/rebuild.md`](backend/rebuild.md:5) 所要求的目标形式。**

对应关系如下：

1. 编排层：[`backend/app/orchestrators/fitness_workflow.py`](backend/app/orchestrators/fitness_workflow.py:1)
2. 边界条件采集子系统：[`backend/app/subsystems/boundary_collector/collector_service.py`](backend/app/subsystems/boundary_collector/collector_service.py:1)
3. 三个领域能力模块：[`backend/app/domains/`](backend/app/domains/)
4. Prompt 聚合器：[`backend/app/core/prompt_aggregator.py`](backend/app/core/prompt_aggregator.py:1)
5. LLM 适配器：[`backend/app/adapters/llm_adapter.py`](backend/app/adapters/llm_adapter.py:1)

同时满足：

- 无内存字典主状态；
- 无原生 sqlite3 状态分支；
- 无重复 domain 实现；
- 无 `new_arch.*` 依赖入口；
- FastAPI 应用可正常 import。

---

## 6. 运行方式

### 启动服务

```bash
uvicorn backend.main:app --reload
```

### 语法与导入检查

```bash
python -m compileall ./backend ./db ./tests
python -c "from backend.main import app; print(app.title)"
```

---

## 7. 后续建议

虽然主架构已经收口完成，但仍建议继续完善：

1. 为 [`backend/app/orchestrators/fitness_workflow.py`](backend/app/orchestrators/fitness_workflow.py:1) 增加更细的集成测试；
2. 为 [`BoundaryCollectorService`](backend/app/subsystems/boundary_collector/collector_service.py:13) 增加状态迁移测试；
3. 对 [`PlanHistory`](db/models.py:67) 增加索引策略和清理策略；
4. 将 [`MCPTemplateManager`](backend/app/services/mcp_template_loader.py:6) 也进一步纳入 Domain 层或 Infrastructure 层的更明确归类。
