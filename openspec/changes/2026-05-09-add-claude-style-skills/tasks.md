## 1. Skill Asset Model

- [x] 1.1 定义 `skills/<name>/SKILL.md` 目录结构与 frontmatter 解析
- [x] 1.2 支持 references / scripts / allowed_tools / role hints 等字段
- [x] 1.3 提供一个最小可运行示例 skill

## 2. Loader And Tooling

- [x] 2.1 扩展 `KnowledgeLoader`，支持列出 skills、生成索引、按层级加载 skill
- [x] 2.2 将 `skill_list` / `skill_load` 接入 LangChain-native tool registry
- [x] 2.3 增加 CLI 入口 `skill-list` 与 `skill-show`

## 3. Context And Runtime Integration

- [x] 3.1 在 context bundle 中为 model path 增加最小 `skills_catalog`，并为 fallback 保留 `matched_skills`
- [x] 3.2 保留 fallback runtime 的 trigger 预匹配与 `skill:` 预加载
- [x] 3.3 调整 model-backed planner / executor / reviewer prompt，使模型可主动决定 `skill_list` / `skill_load`

## 4. Docs And Verification

- [x] 4.1 补充产品文档，说明 skill 目录结构、渐进式披露与验证方式
- [x] 4.2 为 loader / context / CLI 增加测试覆盖
- [x] 4.3 增加一条明确验证模型路径主动 `skill_load` 的集成测试或录屏式示例
  验证记录：`agentos shell --plain --session-id shell2` 输入 code review 任务后，
  `.agentos/sessions/shell2/turn_0001.json` 同时记录了 `skills_catalog`、
  `tool_name=skill_list` 与 `tool_name=skill_load(level=summary)`，说明模型路径已按最小 catalog -> 按需 skill discovery 的链路工作。
