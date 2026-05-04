# Contributing To agentOs

## 开发方式

`agentOs` 采用分阶段、可回看、可打 tag 的实现方式推进。

这意味着：
- 不追求一次性写完整系统
- 每次只完成一个明确范围的 milestone
- 每个 milestone 完成后，仓库必须处于稳定、可理解、可继续发布的状态

## 实施原则

- 优先做对长期结构有价值的最小实现。
- 新能力必须和真实系统需求绑定，避免为了展示框架而硬加无关特性。
- 复杂度递增，但递增必须受控；单个阶段尽量只引入 1 到 2 个关键新点。
- 文档、任务和实现要同步更新，避免规格和代码脱节。

## 环境约定

- 使用项目本地虚拟环境 `.venv-agentos`
- 依赖必须锁定明确版本
- 后续示例、测试和运行命令都默认在 `.venv-agentos` 内执行

## Milestone Workflow

1. 选择当前 milestone 对应的小任务
2. 先补足必要文档或说明
3. 实现最小但可用的代码
4. 添加验证方式
5. 更新 OpenSpec `tasks.md`
6. 满足稳定停止点后再考虑打 tag

## Tag 规则

推荐格式：

```text
v0.<milestone>.<revision>
```

示例：
- `v0.0.0` 仓库初始化
- `v0.1.0` Python 环境基础
- `v0.2.0` 项目骨架

只有在以下条件满足时才打 tag：
- 当前 milestone 目标达成
- 关键文档已更新
- 当前阶段具备基本验证方式
- 仓库状态适合公开展示

## Milestone 完成标准

每个 milestone 至少要满足：
- 新能力已经有代码实现，而不只是设计说明
- 至少有一条命令或测试链路能稳定演示该能力
- OpenSpec 任务勾选状态与仓库实际状态一致
- README 中能看出该阶段是什么、怎么体验
- 仓库可以在这一点打 tag 并长期保留

## Release Checklist

发布前至少检查：
- `make test`
- `git status`
- `.agentos/` 等本地生成态未被加入版本控制
- README / CONTRIBUTING / OpenSpec 任务状态同步
- tag 名称与当前 milestone 一致

详细检查项见 [docs/release-checklist.md](/home/mi/agentOs/docs/release-checklist.md:1)。

## 当前重点

当前阶段优先保证：
- 仓库对外说明清晰
- 环境可复现
- runtime / harness / control plane 分层明确
- LangChain / LangGraph 的引入能逐步覆盖更多真实能力
- milestone 收尾时，代码、文档和 tag 状态保持一致
