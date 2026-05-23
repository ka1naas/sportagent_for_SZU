# 角色与任务说明
你是一个资深的 Python 后端架构师。当前正在接手一个名为“Campus Fitness Scheduler Backend”的 FastAPI 项目。
该项目目前处于“新旧架构并存”的过渡态（技术债务较重）。你的核心任务是：**一步步将系统完全迁移并收敛到新架构，彻底消除冗余代码和临时状态。**

## 目标架构定义
系统必须严格遵循以下分层（目前骨架已在 `new_arch/` 目录下）：
1. **编排层 (Orchestrator)**：`fitness_workflow.py`（唯一业务主干）
2. **边界条件采集子系统**：`BoundaryCollectorService`（唯一状态源）
3. **领域模块 (Domains)**：饮食、训练、天气（三领域模块，无重复实现）
4. **Prompt 聚合器**：`FitnessPromptAggregator`（纯组装，不含业务计算）
5. **LLM 适配器**：`LLMAdapter`（纯模型调用）

---

## 阶段性执行计划 (执行约束)
请严格按照以下 6 个阶段顺序执行。**在每个阶段开始前，请先用工具读取相关文件了解现状；在每个阶段完成后，确保代码没有语法错误，且 FastAPI 服务可以正常启动，然后再进入下一阶段。**

### Phase 1: 统一状态管理与持久化基建 (消除内存状态)
**目标**：彻底消除内存字典，统一使用 SQLAlchemy ORM。
1. 阅读 `backend/app/routers/plan_routes.py` (查找 `PLAN_STORE`) 和 `new_arch/orchestrators/fitness_workflow.py` (查找 `_PLAN_HISTORY_STORE`)。
2. 在 `db/models.py` 中新增 `PlanHistory` (或类似) 模型，用于持久化存储计划草案和对话历史。
3. 重构现有代码，移除所有基于内存 `dict` 的状态存储，将其替换为对数据库的 CRUD 操作。
4. 确保 `db/database.py` 提供统一的 DB Session 依赖，供新架构调用。

### Phase 2: 收敛边界条件采集子系统 (单一事实源)
**目标**：解决原生 sqlite 与 ORM 混用、双表并存的问题。
1. 对比旧的 `backend/app/services/chat_session_service.py` (`chat_sessions` 表) 和新的 `new_arch/subsystems/boundary_collector/collector_service.py` (`boundary_sessions` 表)。
2. 将这两种采集逻辑统一。在 `db/models.py` 中定义一个标准的 SQLAlchemy 模型来存储会话状态与问卷数据。
3. 改造 `BoundaryCollectorService`，让其使用新的 SQLAlchemy DB Session，并支持旧版五步问卷所需的所有状态流转。
4. 在应用中移除对原生 `sqlite3` 的调用，安全废弃 `ChatSessionService`。

### Phase 3: 领域能力去重与完善 (Domain 层收口)
**目标**：干掉 `backend/app/services/` 下的重复逻辑，补全 `new_arch/domains/` 的缺失实现。
1. **天气领域**：阅读 `backend/app/services/weather_service.py` / `venue_analyzer.py`，将其调用真实 API 的逻辑迁移到 `new_arch/domains/weather_domain.py`，替换掉目前的 mock 天气实现。
2. **饮食领域**：将 `backend/app/services/nutrition_calc.py` 和 `diet_planner.py` 的有效逻辑完全合并到 `new_arch/domains/diet_domain.py`。
3. **训练领域**：将 `backend/app/services/mcp_template_loader.py` 的真实读取逻辑迁移到 `new_arch/domains/exercise_domain.py`。
4. 确保所有 `new_arch/domains/` 模块都能独立工作，提供清晰的对内 API。

### Phase 4: 净化 Prompt 与 LLM 适配器
**目标**：职责剥离，确保组装与请求分离。
1. 分析旧的 `backend/app/services/dispatch_engine.py` (`build_prompt_context`)。
2. 将其内部的“领域计算”调用统统剥离（交由编排层处理）。
3. 将纯粹的“文本拼装”逻辑完整迁移到 `new_arch/core/prompt_aggregator.py` (`FitnessPromptAggregator`)。
4. 检查 `backend/app/services/llm_service.py`，将其核心调用逻辑迁移并适配到 `new_arch/adapters/llm_adapter.py`，然后废弃旧的 `llm_service.py` 和 `dispatch_engine.py`。

### Phase 5: 路由器瘦身与编排层接管 (重构入口层)
**目标**：Router 层只负责 HTTP 协议转换，业务逻辑全部下沉到编排层。
1. 完善 `new_arch/orchestrators/fitness_workflow.py` 的接口，使其能接收用户输入，内部调用统一的领域模块、聚合器和适配器，并操作新的 DB 持久化逻辑。
2. 大幅重构 `backend/app/routers/`（特别是 `plan_routes.py` 和 `chat.py`）。
3. 移除路由函数中直接调用 domain/service 的逻辑，把它们改造为仅仅是 `fitness_workflow.py` 的透传入口。
4. 确保在单次请求中，不再存在“一半调旧 service，一半调新 arch”的缝合怪代码。

### Phase 6: 文件与目录清理 (最终梳理)
1. 删除 `backend/app/services/` 目录下所有已经被废弃的旧文件（如 `chat_session_service.py`, `dispatch_engine.py`, `llm_service.py`, `venue_analyzer.py` 等）。
2. 将 `new_arch/` 及其子目录重命名或直接合并到 `backend/app/` 的标准结构中（视当前项目文件组织规范而定，例如变成 `backend/app/domains/`、`backend/app/orchestrators/` 等），去除“新旧并存”的目录感。
3. 更新 `README.md`，真实反映完成后的最新架构。

---

## 你的工作指引
1. 每完成一个 Phase，请在对话中向我做一个简短的总结汇报，说明你修改了哪些文件，以及当前系统是否能够正常 import 和启动。
2. 遇到依赖循环或无法确认的业务字段映射时，停止修改并向我提问。
3. 绝不能简单地把旧代码注释放置，请直接删除废弃代码，保持代码库整洁。
4. 请以 Phase 1 为起点，开始分析文件并给出你对于 Phase 1 的修改方案，待我确认后开始写代码。