# agentOs

`agentOs` 是一个分阶段构建的 coding-agent harness 项目。

目标不是做一个一次性 demo，而是在可运行、可发布、可继续演进的前提下，一步一步实现一个具备实际可用性的 agent 系统。项目会把 `agent runtime`、`harness`、`task control plane` 和 `LangChain/LangGraph` 的关键能力逐层展开，保证每个阶段都能独立理解、独立提交、独立打 tag。

## 当前状态

当前仓库已经完成 `M0` 到 `M9`，处于第一条基础 change 的收尾阶段。

已完成：
- OpenSpec proposal / design / specs / tasks
- 仓库公开规范与版本节奏
- Harness foundation
- LangGraph runtime v1
- Task control plane
- Context and knowledge management
- Advanced LangChain / LangGraph routing
- Async and isolated execution
- Multi-agent coordination control plane

当前得到的是一个“具备主要核心部件的 agent/harness 学习型底座”，还不是完整的 Claude Code 级成品。后续新的 change 会继续推进真实 loop、后台结果回流、真实 delegated execution、权限体系和更强的可用性。

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
make run-knowledge
make exec
make bg-run
make bg-list
make workspace-create
make workspace-list
make unit-list
make task-list
make knowledge-list
make context-demo
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

当前阶段的最小任务命令：

```bash
PYTHONPATH=src .venv-agentos/bin/python -m agentos.cli task-create "Setup project"
PYTHONPATH=src .venv-agentos/bin/python -m agentos.cli task-create "Write tests" --blocked-by 1
PYTHONPATH=src .venv-agentos/bin/python -m agentos.cli task-list
PYTHONPATH=src .venv-agentos/bin/python -m agentos.cli task-complete 1
```

### M6: Context And Skill Management

学习目标：
- 理解为什么知识不能一次性塞进一个 prompt
- 理解为什么长会话必须压缩上下文

预期产出：
- knowledge topic 按需加载
- context compaction 示例
- 持久化 context snapshot

当前阶段的最小体验命令：

```bash
make knowledge-list
PYTHONPATH=src .venv-agentos/bin/python -m agentos.cli knowledge-load langgraph-runtime
make context-demo
```

### M7: Advanced LangChain / LangGraph

学习目标：
- 系统掌握比入门示例更完整的框架能力

预期产出：
- structured output
- routing / branching
- persistence / memory
- human-in-the-loop
- tracing / observability

当前阶段的最小体验命令：

```bash
make run
make run-knowledge
PYTHONPATH=src .venv-agentos/bin/python -m agentos.cli run "run: rm temp.txt"
PYTHONPATH=src .venv-agentos/bin/python -m agentos.cli run "run: rm temp.txt" --approve
```

### M8: Async And Isolated Execution

学习目标：
- 理解后台执行与隔离执行面的价值

预期产出：
- 后台执行路径
- 状态回流机制
- 隔离工作区设计

当前阶段的最小体验命令：

```bash
make bg-run
make bg-list
PYTHONPATH=src .venv-agentos/bin/python -m agentos.cli bg-status <job-id>
make workspace-create
make workspace-list
```

### M9: Multi-Agent Coordination

学习目标：
- 理解委派、协调状态和结果汇总

预期产出：
- delegation model
- coordination state
- 第一版受控多 agent 流程

当前阶段的最小体验命令：

```bash
PYTHONPATH=src .venv-agentos/bin/python -m agentos.cli unit-create "Inspect backend" --role researcher
PYTHONPATH=src .venv-agentos/bin/python -m agentos.cli unit-create "Write patch" --role builder --depends-on 1
make unit-list
PYTHONPATH=src .venv-agentos/bin/python -m agentos.cli unit-complete 1 --result "inspection done"
make unit-list
```

### M10: Release Discipline

学习目标：
- 让仓库保持长期可发布、可回滚、可复现

预期产出：
- milestone 完成标准
- release checklist
- 文档一致性检查

当前阶段的收尾要求：
- `make test` 通过
- 体验命令与 README 保持一致
- 生成态目录如 `.agentos/` 不进入提交
- milestone tag 与代码状态一致

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
- `v0.5.0`：task control plane 完成
- `v0.6.0`：context and knowledge management 完成
- `v0.7.0`：advanced LangChain / LangGraph routing 完成
- `v0.8.0`：async and isolated execution 完成
- `v0.9.0`：multi-agent coordination 完成

规则：
- 只有 milestone 到达稳定停止点时才打 tag
- 中间零碎提交不打 tag
- 若同一 milestone 需要修正文档或小修复，可递增 patch 版本

## Milestone Completion Criteria

每个 milestone 要满足以下条件，才算到达稳定停止点：

- 该阶段的主学习目标已经体现在代码中，而不是只存在于说明里
- 至少有一条 CLI 或测试链路可以演示新能力
- README 中有对应阶段的体验命令或说明
- `openspec` 任务状态与实现状态一致
- 仓库可以在这一点上停止并打 tag，而不会留下隐含的补丁工作

## Release Hygiene

- 里程碑发布前运行：`make test`
- 检查本地生成态目录如 `.agentos/` 没有被纳入提交
- 按 [docs/release-checklist.md](/home/mi/agentOs/docs/release-checklist.md:1) 完成发布检查

## 下一步方向

这条基础 change 收尾后，更适合进入新 change 的方向包括：
1. 让 runtime 进入真正的 agent loop，而不是当前的单次有向流程
2. 让后台任务结果真正重新喂回 graph
3. 把 coordination control plane 接成真实 delegated execution
4. 引入更完整的权限体系与人审流程
5. 增加更接近真实 coding agent 的可用性层

## 说明

这个仓库会持续保留“教学可读性”，但不会把自己限制成教学 demo。随着 milestone 推进，系统复杂度会增加，目标是让你在完成项目后不仅理解 agent/harness 的实现方式，也能较系统地掌握 LangChain / LangGraph 在真实工程中的用法。
