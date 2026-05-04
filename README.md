# agentOs

`agentOs` 是一个分阶段构建的 coding-agent harness 项目。

目标不是做一个一次性 demo，而是在可运行、可发布、可继续演进的前提下，一步一步实现一个具备实际可用性的 agent 系统。项目会把 `agent runtime`、`harness`、`task control plane` 和 `LangChain/LangGraph` 的关键能力逐层展开，保证每个阶段都能独立理解、独立提交、独立打 tag。

## 当前状态

当前仓库处于第 0 阶段：仓库初始化与实施规划。

已完成：
- OpenSpec proposal / design / specs / tasks
- 第一版仓库公开规范

接下来会按 milestone 小步推进，不会直接跳到完整实现。

## Environment Setup

当前阶段统一使用 Python `3.10` 和项目本地虚拟环境 `.venv-agentos`。

```bash
python3 -m venv .venv-agentos
source .venv-agentos/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt -r requirements-dev.txt
```

完成安装后，运行：

```bash
bash scripts/verify_env.sh
```

这个验证脚本会检查：
- 当前虚拟环境是否为 `.venv-agentos`
- 关键依赖是否可导入
- Python 主版本是否符合当前阶段要求

开发阶段的常用命令：

```bash
make status
make run
make exec
make test
make verify-env
```

## 项目原则

- 一步一步实现，每个阶段只引入少量新概念。
- 每个 milestone 都必须是一个稳定停止点。
- 优先构建可用系统，不做脱离实际需求的框架炫技。
- LangChain / LangGraph 的引入必须服务于真实 runtime 能力，而不是只做最小示例。
- 所有依赖安装到项目虚拟环境 `.venv-agentos` 中，并锁定明确版本。

## Milestone Map

### M0: Repository Bootstrap

学习目标：
- 理解项目目标、范围和推进方式
- 建立公开仓库所需的基本文件

预期产出：
- `README.md`
- `.gitignore`
- `CONTRIBUTING.md`
- 明确的 milestone/tag 规则

### M1: Python Environment Foundation

学习目标：
- 建立可复现的 Python 开发环境
- 理解为什么 agent 工程需要稳定依赖基础

预期产出：
- `.venv-agentos` 初始化说明
- 锁版本 `requirements.txt`
- 基础安装验证方式

### M2: Project Skeleton

学习目标：
- 理解 runtime、harness、CLI、config 的初始分层

预期产出：
- 最小 Python 包结构
- CLI 入口
- import / smoke tests

### M3: Harness Foundation

学习目标：
- 理解命令执行边界与 agent 逻辑边界

预期产出：
- 执行器接口
- 第一版本地命令执行器
- 基础执行测试

### M4: LangGraph Runtime v1

学习目标：
- 掌握最小 LangGraph 状态图
- 区分模型决策阶段与工具执行阶段

预期产出：
- 第一版 state model
- 最小 graph loop
- tool adapter

当前阶段的最小运行约定：
- 使用 `run: <command>` 形式触发 tool execution
- 例如 `make run` 会通过 LangGraph 跑一个 `pwd` 示例
- 非 `run:` 任务会停在 model step，并返回指导信息

### M5: Task Control Plane

学习目标：
- 理解为什么任务状态不能只放在对话上下文里
- 学会把多步任务落盘并支持恢复

预期产出：
- 持久化任务模型
- 依赖关系
- reload / transition tests

### M6: Context And Skill Management

学习目标：
- 理解长会话 context pressure
- 学会按需加载知识和技能

预期产出：
- 知识/技能加载机制
- 上下文管理策略
- 对应演示或测试

### M7: Advanced LangChain / LangGraph

学习目标：
- 系统掌握比入门示例更完整的框架能力

预期产出：
- structured output
- routing / branching
- persistence / memory
- human-in-the-loop
- tracing / observability

### M8: Async And Isolated Execution

学习目标：
- 理解后台执行与隔离执行面的价值

预期产出：
- 后台执行路径
- 状态回流机制
- 隔离工作区设计

### M9: Multi-Agent Coordination

学习目标：
- 理解委派、协调状态和结果汇总

预期产出：
- delegation model
- coordination state
- 第一版受控多 agent 流程

### M10: Release Discipline

学习目标：
- 让仓库保持长期可发布、可回滚、可复现

预期产出：
- milestone 完成标准
- release checklist
- 文档一致性检查

## Tag Convention

每个稳定 milestone 完成后打一个 Git tag，格式如下：

```text
v0.<milestone>.<revision>
```

当前建议：
- `v0.0.0`：仓库初始化完成
- `v0.1.0`：环境基础完成
- `v0.2.0`：项目骨架完成
- `v0.3.0`：harness foundation 完成
- `v0.4.0`：LangGraph runtime v1 完成

规则：
- 只有 milestone 到达稳定停止点时才打 tag
- 中间零碎提交不打 tag
- 若同一 milestone 需要修正文档或小修复，可递增 patch 版本

## 近期实施顺序

当前优先级：
1. 仓库基础文件
2. Python 虚拟环境与锁版本依赖
3. 最小项目骨架
4. 第一版 harness
5. 第一版 LangGraph runtime

## 说明

这个仓库会持续保留“教学可读性”，但不会把自己限制成教学 demo。随着 milestone 推进，系统复杂度会增加，目标是让你在完成项目后不仅理解 agent/harness 的实现方式，也能较系统地掌握 LangChain / LangGraph 在真实工程中的用法。
