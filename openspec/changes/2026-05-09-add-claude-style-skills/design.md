## Context

`agentOs` 已经具备三块基础设施：

- demand-loaded knowledge / skill loader 雏形
- role-aware context bundle
- model-backed planner / executor / reviewer runtime

但如果直接把 skill 设计成“命中 trigger 就强行注入”，模型路径会退化成半规则系统。Claude Code 风格 skill 的关键不是“先匹配”，而是“先让模型知道有哪些可用 skill，再让模型按需要逐层取用”。因此这里需要把 skill 信息分成两层：

- 发现层：列出有哪些 skills 可用
- 加载层：模型或 runtime 在需要时调用 `skill_load`

## Goals / Non-Goals

**Goals**

- 支持用户在本地新增 `skills/<name>/SKILL.md`
- 让 context bundle 对模型只暴露最小 skills catalog
- 保留确定性 fallback 的 trigger 预匹配
- 让模型路径可主动决定是否调用 `skill_load`
- 保持 skill 读取的渐进式披露，避免一次性把全部 reference 注入 prompt

**Non-Goals**

- 这条 change 不实现复杂的动态工具权限收缩
- 不做远程 skill marketplace
- 不做多轮自主 skill 学习或自动生成 skill

## Decisions

### 1. 将 skills 信息拆成 `skills_catalog` 与 `matched_skills`

`skills_catalog` 表示当前仓库可用的最小技能目录，只保留 `name`、`description`、`when_to_use`，是模型路径的主要输入。

`matched_skills` 表示基于 trigger 的弱提示，主要服务于 fallback 路径，同时也可作为模型路径的次级 hint。

理由：

- 避免模型路径被硬匹配绑死
- 保留 fallback 的确定性能力
- 便于在同一个 context bundle 中清晰表达“可用能力”和“规则猜测”

### 2. model-backed bundle 只保留最小 catalog

理由：

- skill 的目标是降低默认上下文成本，而不是把 skill 正文提前塞进 prompt
- 最小 catalog 已足够支持“是否要进一步加载某个 skill”的判断
- inspectability 仍可通过 `skills_catalog` 和工具结果保留

### 3. 保持 `skill_load` 作为统一渐进加载入口，并补充 `skill_list`

继续复用现有 `skill_load(name, level, target)`，并补充 `skill_list(role=...)`。当前支持：

- `skill_list`
- `summary`
- `full`
- `reference`
- `script`

理由：

- 保持工具面稳定
- `skill_list` 能在 context 被压缩后补充最新可用 skill 目录
- 与 Claude Code 式“先摘要、再深挖”使用习惯一致

### 4. model-backed runtime 只把 `matched_skills` 当 hint

planner / executor / reviewer 的 prompt 应明确：

- 可以查看 available skills
- 可以主动决定是否 `skill_list` / `skill_load`
- matched skills 只是提示，不是强制路由

理由：

- 这是“模型主动识别调用”的核心
- 避免当前系统被关键词匹配主导

### 5. fallback runtime 继续自动预加载

fallback 路径没有真实模型判断能力，因此保留当前 `match_skills(task)` 后自动插入 `skill:` 任务的做法。

理由：

- fallback 的目标是稳定可用，不是拟真智能性
- 这样可以让双路径共享同一份 skills 资产，而不需要维护两套机制

## Data Shape

`context bundle` 新增或明确以下字段：

- `skills_catalog`: 当前仓库中可见的最小 skill 目录
- `matched_skills`: 当前 task 基于 trigger 命中的 skill 摘要列表
- `active_skills`: 向后兼容别名，当前等于 `matched_skills`
- `skills_hint`: 对 catalog / matched 的极小摘要

## Risks / Trade-offs

- skills 过多时最小 catalog 仍可能变长
  - Mitigation: 默认只暴露紧凑字段，并可通过 `skill_list` 在需要时补充
- trigger 匹配可能误命中
  - Mitigation: 明确它只是 hint，不作为模型主路径硬路由
- 模型可能看见最小 catalog 但未主动调用
  - Mitigation: 在 executor state modifier 中明确提醒先 `skill_list` / `skill_load`

## Validation

- loader 测试：列出 skill、索引、summary/full/reference/script 加载
- context 测试：model path 暴露 `skills_catalog`，fallback path 保留 `matched_skills`
- CLI 测试：`skill-list`、`skill-show`
- 集成验证：model-backed shell 下自然语言任务可看到最小 catalog，并在 tool results 中出现 `skill_list` / `skill_load`
