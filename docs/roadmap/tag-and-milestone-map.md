# Tag 与里程碑映射

本文是当前仓库唯一维护的 tag 映射真相源。

## 最终映射

| Tag | Commit | 阶段 | 主要能力 |
| --- | --- | --- | --- |
| `v0.1.0` | `381a638` | M0 | 仓库与环境基础 |
| `v0.2.0` | `731ceb0` | M2 | 初始项目骨架 |
| `v0.3.0` | `a410286` | M3 | harness foundation |
| `v0.4.0` | `d410b9d` | M4 | LangGraph runtime v1 |
| `v0.5.0` | `bdfcc12` | M5 | task control plane |
| `v0.6.0` | `8633958` | M6 | context and knowledge management |
| `v0.7.0` | `cc12f7d` | M7 | advanced LangChain / LangGraph routing |
| `v0.8.0` | `565cc68` | M8 | async and isolated execution |
| `v0.9.0` | `2a35c49` | M9 | multi-agent coordination control plane |
| `v0.10.0` | `70f93f5` | M10 | 第一条 change 的发布纪律收尾 |
| `v0.11.0` | `b6ce5de` | M11 | resumable runtime loop |
| `v0.12.0` | `e4cbe58` | M12 | background result re-entry |
| `v0.13.0` | `7977f3e` | M13 | delegated work execution |
| `v0.14.0` | `62c19bf` | M14 | 第二条 change 收尾与 real agent loop 稳定化 |
| `v0.15.0` | `5e166e7` | M15 | session persistence |
| `v0.16.0` | `85d01a0` | M16 | session resume flow |
| `v0.17.0` | `b4a67d0` | M17 | bounded session continuation |
| `v0.18.0` | `b93f727` | M18 | structured tool registry |
| `v0.19.0` | `9c8c78e` | M19 | task-aware context bundles |
| `v0.20.0` | `d4bc318` | M20 | bounded role workflow |
| `v0.21.0` | `0d55499` | M21 | interactive CLI workflows |
| `v0.22.0` | `b73ff95` | 4.x-1 | interactive shell milestone |
| `v0.23.0` | `e3c1a8c` | 4.x-2 | structured role agent runtime |
| `v0.24.0` | `9e96666` | 4.x-3 | context policy runtime |
| `v0.25.0` | `fbf0db2` | 4.x-4 | LangChain-native tool runtime |
| `v0.26.0` | `9241dda` | 4.x-5 | model-backed agent runtime |
| `v0.27.0` | `ca0cb57` | 4.x-6 | interactive shell change 收尾 |
| `v0.28.0` | `2c9af50` | 5.x-1 | packaged `agentos` CLI 产品化 |
| `v0.29.0` | `fac07e7` | 5.x-2 | production context engine |

## 本次修正动作

- `v0.5.0` 从 `d410b9d` 改到 `bdfcc12`
- 新增 `v0.6.0` 到 `8633958`
- `v0.12.0` 从 `0bf0429` 改到 `e4cbe58`
- `v0.14.0` 从 `7977f3e` 改到 `62c19bf`
- `v0.19.0` 从 `b93f727` 改到 `9c8c78e`
- `v0.22.0` 从 `97f2938` 改到 `b73ff95`
- `v0.23.0` 保持在 `e3c1a8c`
- `v0.24.0` 从 `b4bb7e2` 改到 `9e96666`
- `v0.25.0` 从 `8a6b2cc` 改到 `fbf0db2`
- `v0.28.0` 新增到 `2c9af50`

## 单用户仓库同步说明

如果历史 tag 已经推送到远端，修正后需要显式同步：

```bash
git push origin --delete v0.5.0 v0.6.0 v0.12.0 v0.14.0 v0.19.0 v0.22.0 v0.24.0 v0.25.0 v0.28.0
git push origin v0.5.0 v0.6.0 v0.12.0 v0.14.0 v0.19.0 v0.22.0 v0.24.0 v0.25.0 v0.28.0
```

如果本地还有旧 tag 缓存，也需要执行：

```bash
git fetch --tags --force
```
