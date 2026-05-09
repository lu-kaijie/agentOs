# agentOs

`agentOs` 是一个基于 `LangChain` 与 `LangGraph` 构建的 coding-agent shell。它不是单次演示脚本，而是一个可安装、可启动、可持续交互的命令行产品原型。

当前形态已经具备这些核心能力：

- 安装后直接通过 `agentos` 启动
- 常驻交互式 shell，而不是每轮都重新敲长命令
- 真实模型主路径与 deterministic fallback 双路径
- LangChain-native tool runtime
- LangGraph 驱动的 role / context / tool / session 工作流
- session 持久化、resume、watch、上下文整理与长期记忆骨架

## 快速开始

推荐在项目虚拟环境 `.venv-agentos` 中安装：

```bash
python3 -m venv .venv-agentos
source .venv-agentos/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m pip install -e .
cp .env.example .env
```

至少填写：

```env
OPENAI_API_KEY=...
OPENAI_BASE_URL=...
```

启动：

```bash
agentos
```

常用命令：

```bash
agentos
agentos shell
agentos run "请阅读 README.md，然后总结当前项目状态" --model
agentos status
agentos session-show shell
agentos watch shell
```

## 文档导航

产品使用：

- [产品概览](docs/product/overview.md)
- [快速上手](docs/product/quickstart.md)
- [详细使用](docs/product/usage.md)
- [Skills 机制](docs/product/skills.md)
- [配置说明](docs/product/configuration.md)
- [体验与验收](docs/product/verification.md)

版本与发布：

- [版本历史](docs/roadmap/release-history.md)
- [Tag 与里程碑映射](docs/roadmap/tag-and-milestone-map.md)
- [文档信息架构](docs/roadmap/documentation-information-architecture.md)
- [本次整理前清单](docs/roadmap/pre-cleanup-inventory.md)
- [发布检查清单](docs/roadmap/release-checklist.md)
- [整理核对记录](docs/roadmap/cleanup-verification.md)

学习与源码：

- [一步一步构建历程](docs/learn/build-journey.md)
- [Change 地图](docs/learn/change-map.md)
- [系统总览](docs/architecture/system-overview.md)
- [持续交互主链路详解](docs/architecture/interactive-mainline-deep-dive.md)
- [运行链路](docs/architecture/runtime-flow.md)
- [上下文引擎](docs/architecture/context-engine.md)
- [工具运行时](docs/architecture/tool-runtime.md)
- [Session 与记忆](docs/architecture/session-and-memory.md)

面试与产品判断：

- [核心功能与取舍](docs/interview/core-features-and-tradeoffs.md)
- [LangChain / LangGraph 用法](docs/interview/langchain-langgraph-usage.md)
- [与 Claude Code 的差距](docs/interview/product-gap-vs-claude-code.md)

## 当前定位

`agentOs` 已经是一个“可运行、可持续交互、可做常见 coding 任务”的 agent shell 原型，但还不是完整商业级产品。它更接近：

- 一个 LangChain / LangGraph 风格的 Claude Code 类产品原型
- 一个可演示、可扩展、可继续工程化的终端 agent
- 一个适合继续演进到更强上下文管理、更多 agent 协作和更好产品界面的基础版本

## 开发说明

仓库开发常用命令：

```bash
make status
make shell
make shell-model
make run-model
make test
```

如果只想确认当前环境：

```bash
bash scripts/verify_env.sh
```
