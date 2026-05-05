# 版本历史

## 总览

`agentOs` 的演进可以分成五段：

1. M0-M10：仓库底座、harness、LangGraph runtime、control plane
2. M11-M14：真实 agent loop 雏形
3. M15-M21：session、tool、context、role、interactive CLI
4. v0.22-v0.27：interactive model-backed agent shell
5. v0.28-v0.29：产品化收尾与 production context engine

## 第一阶段：M0-M10

- `v0.1.0` 到 `v0.3.0`
  - 建立仓库、环境、初始骨架和 harness
- `v0.4.0`
  - 第一个 LangGraph runtime
- `v0.5.0` 到 `v0.9.0`
  - task、context、routing、execution control、coordination 逐步接上
- `v0.10.0`
  - 第一条 change 的发布纪律与里程碑规则收尾

## 第二阶段：M11-M14

- `v0.11.0`
  - resumable runtime loop
- `v0.12.0`
  - background result re-entry
- `v0.13.0`
  - delegated work execution
- `v0.14.0`
  - real agent loop 稳定化并完成第二条 change 收尾

## 第三阶段：M15-M21

- `v0.15.0`
  - session persistence
- `v0.16.0`
  - session resume flow
- `v0.17.0`
  - bounded continuation
- `v0.18.0`
  - structured tool registry
- `v0.19.0`
  - task-aware context bundles
- `v0.20.0`
  - bounded role workflow
- `v0.21.0`
  - interactive CLI workflows

## 第四阶段：interactive model-backed agent shell

- `v0.22.0`
  - 常驻 interactive shell
- `v0.23.0`
  - structured role agent runtime
- `v0.24.0`
  - context policy runtime
- `v0.25.0`
  - LangChain-native tool runtime
- `v0.26.0`
  - model-backed agent runtime
- `v0.27.0`
  - 整条 change 收尾

## 第五阶段：产品化收尾

- `v0.28.0`
  - 安装后直接 `agentos` 启动
- `v0.29.0`
  - production context engine

## 如何阅读历史

如果你是为了使用产品：

- 先看 [../product/quickstart.md](../product/quickstart.md)

如果你是为了看每一阶段怎么做出来：

- 先看 [../learn/build-journey.md](../learn/build-journey.md)

如果你是为了核对 tag：

- 直接看 [tag-and-milestone-map.md](tag-and-milestone-map.md)
