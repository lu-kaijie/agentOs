## Why

当前 `agentOs` 已经有 demand-loaded knowledge、LangChain-native tools 和 model-backed executor，但还缺少一套像 Claude Code 那样可由用户自定义、可渐进披露、可被模型主动调用的 skill 机制。现有实现更接近“task 文本硬匹配后注入提示”，这对 deterministic fallback 足够，但对真实模型主路径不够自然，也不利于后续扩展更多 skill。

这条 change 的目标是把 skill 从“关键词附加提示”提升为“用户定义的本地能力包”，并明确两条执行路径的职责：

- model-backed 主路径：默认只暴露最小 skill catalog，由模型自主决定是否调用 `skill_list` / `skill_load`
- fallback 路径：继续使用确定性的 trigger 匹配和预加载，保证无模型时仍可工作

## What Changes

- 引入本地 `skills/<name>/SKILL.md` 目录约定，支持 description、triggers、role hints、references、scripts、allowed_tools 等字段。
- 扩展 `KnowledgeLoader`，支持列出 skills、生成最小 catalog、渐进加载 skill 摘要 / 正文 / reference / script。
- 扩展 context pipeline，使 model path 默认只暴露 `skills_catalog`，并保留 fallback 使用的 `matched_skills`。
- 调整 model-backed planner / executor / reviewer prompt，使模型基于最小 catalog 自主选择是否调用 `skill_list` / `skill_load`，而不是把规则匹配当成主入口。
- 保留 fallback runtime 的预匹配能力，用于自动插入 `skill: <name>` 任务。
- 新增示例 skill、CLI 展示入口和产品文档。

## Capabilities

### New Capabilities

- `claude-style-skills`: 支持用户自定义本地 skill，并以渐进式披露方式供 agent 使用。

### Modified Capabilities

- `context-and-skill-management`: 从“可按任务加载知识”扩展为“可暴露最小 skills catalog、保留匹配提示并支持主动加载 skill 内容”。
- `model-backed-agent-runtime`: 从“模型可消费 context bundle”扩展为“模型可根据最小 skill catalog 主动选择和调用 skills”。

## Impact

- 影响 `knowledge loader`、`context bundle`、`model-backed runtime prompt`、fallback runtime 初始化、CLI 和测试。
- 会新增 `skills/` 示例目录与技能文档。
- 不改变现有 harness、安全边界、工具注册主结构。

## Acceptance Shape

完成后，贡献者应能：

- 在 `skills/` 下新增一个自定义 `SKILL.md`
- 通过 `agentos skill-list` / `agentos skill-show` 看到该 skill
- 在 model-backed shell 中让模型看到最小 skill catalog，并在需要时主动触发 `skill_list` / `skill_load`
- 在 fallback 路径中通过 trigger 命中 skill 并完成预加载
