## Why

这个项目需要一条“可学习、可暂停、可迭代”的实现路径，用来一步一步搭建一个类似 coding agent 的 `agentOs`，而不是一开始就堆出一个难以理解的成品。与此同时，这个项目也不能停留在教学 demo 层面，而是要逐步发展成一个具备实际可用性和一定复杂度的系统。现在先把这条路径设计清楚，可以保证后续仓库按小步可验证的里程碑推进，并且每一步都能学到 agent 与 harness 的关键机制，以及 LangChain/LangGraph 更完整的能力版图。

## What Changes

- 为 `agentOs` 定义分阶段实现路线，覆盖仓库初始化、Python 虚拟环境、精确版本依赖、harness 基础结构，以及首个基于 LangChain/LangGraph 的 agent runtime。
- 明确“以学习为导向”的阶段边界，让每个里程碑只聚焦一层核心能力，例如命令执行、状态编排、工具接入、提示词与运行时结构。
- 将项目目标定义为“逐步做成可用系统”而非一次性 demo，后续阶段需要持续增加复杂度、可维护性和真实使用价值。
- 扩展 LangChain/LangGraph 的学习覆盖面，使项目不仅包含基础 graph loop，还要为后续引入更丰富的框架能力预留明确路线，例如 structured output、tool binding、state modeling、multi-step routing、memory/persistence、human-in-the-loop、observability 或 evaluation。
- 将 agent 控制面纳入长期范围，包括持久化任务系统、后台任务、上下文管理、知识/技能按需加载、多 agent 协作以及隔离执行工作区。
- 增加面向 GitHub 发布所需的仓库规范，包括基础说明文件、阶段文档以及每个阶段完成后的 tag 发布节奏。
- 规定依赖安装必须使用项目相关命名的本地虚拟环境 `.venv-agentos`，并通过精确版本锁定的 `requirements` 文件保证可复现。

## Capabilities

### New Capabilities
- `guided-implementation-journey`: 将项目定义为一系列小步推进的里程碑，并为每一步设置明确学习目标和停止点。
- `langgraph-agent-runtime`: 定义首个基于 LangChain/LangGraph 的 agent runtime，让实现过程覆盖图编排的核心概念。
- `development-harness-foundation`: 定义本地 harness 的职责边界、环境初始化方式以及命令执行接口。
- `advanced-framework-coverage`: 定义 LangChain/LangGraph 在项目中的进阶能力覆盖范围，确保学习结果不止于入门用法。
- `task-orchestration-system`: 定义可持久化的任务系统，用于支持多步任务、依赖关系和跨会话恢复。
- `context-and-skill-management`: 定义上下文压缩、知识装载和技能加载的机制，使 agent 能在更长会话中保持可用。
- `async-and-isolated-execution`: 定义后台任务与隔离执行工作区，支持更复杂、更长时的并行工作流。
- `multi-agent-coordination`: 定义多 agent 协作、任务分派和结果汇总的基础能力。
- `repository-release-discipline`: 定义适合公开发布到 GitHub 的仓库规范与阶段性打 tag 要求。

### Modified Capabilities

- None.

## Impact

- 影响仓库目录结构、实现顺序以及后续协作方式。
- 引入 Python 环境与依赖规范，包括 `.venv-agentos` 和精确版本锁定的 `requirements` 文件。
- 引入 LangChain 与 LangGraph 作为首个 agent runtime 的主要框架依赖。
- 提高后续实现复杂度要求，项目需要逐步覆盖更多真实 agent 系统常见机制，而不是只做最小演示链路。
- 增加对任务持久化、异步执行、上下文治理、技能装载和并行隔离执行等控制面能力的要求。
- 增加对 GitHub 可发布文件、阶段说明和轻量发布检查点的要求。
