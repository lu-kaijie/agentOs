# Change 地图

## 第一条 change

目标：

- 先搭出基础工程
- 理解 harness、LangGraph runtime、control plane 的分层

产出：

- M0-M10
- 从仓库初始化走到第一条 change 收尾

## 第二条 change

目标：

- 把 runtime 从静态流程推进为更真实的 agent loop

产出：

- M11-M14
- loop、background re-entry、delegated execution、稳定化收尾

## 第三条 change

目标：

- 让系统进入“基本可用 agent”阶段

产出：

- M15-M21
- session、tool、context、role、interactive CLI

## 第四条 change

目标：

- 让 agent 变成真实模型驱动的常驻交互式 shell

产出：

- `v0.22.0` 到 `v0.27.0`
- role agent runtime、context policy、LangChain-native tool runtime、model-backed shell

## 第五条 change

目标：

- 做产品化与上下文引擎收尾

产出：

- `v0.28.0`
  - packaged CLI
- `v0.29.0`
  - production context engine
