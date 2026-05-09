# Skills 机制

## 概览

`agentOs` 现在支持用户自定义 skill，并在两条执行路径里复用：

- model-backed 主路径
- deterministic fallback 路径

skill 的目标不是把所有规则直接塞进 system prompt，而是提供一套符合 Claude Code 风格的渐进式披露机制：

1. 默认上下文只暴露极小的 skill catalog：`name + description + when_to_use`
2. model-backed 路径不预先注入 `SKILL.md` 正文
3. fallback 路径可按 trigger 预匹配 skill 作为内部提示
4. 模型如果需要更多细节，再主动调用 `skill_load`
5. 需要时再读 `SKILL.md` 主体、`references/` 或 `scripts/`

## 目录结构

每个 skill 放在 `skills/<name>/` 下，入口文件固定为 `SKILL.md`：

```text
skills/
  code-review/
    SKILL.md
    references/
      checklist.md
      examples.md
    scripts/
      gather_diff_context.py
```

约定：

- `SKILL.md`
  skill 主入口，包含描述、触发条件、角色提示、references 和 scripts 索引
- `references/`
  补充规则、checklist、案例、模板
- `scripts/`
  程序化上下文收集脚本或辅助脚本

## `SKILL.md` 格式

推荐格式：

```md
---
name: code-review
description: Review code changes for bugs, regressions, and missing tests.
triggers:
  - code review
  - review
  - analyze diff
roles:
  planner:
    hint: Focus on changed scope and risk areas.
  executor:
    hint: Read changed files first, then inspect behavior and tests.
  reviewer:
    hint: Prioritize regressions, correctness, and missing verification.
references:
  - references/checklist.md
  - references/examples.md
scripts:
  - scripts/gather_diff_context.py
allowed_tools:
  - repo_search
  - file_read
  - shell_command
  - test_run
---

# Code Review Skill

Use this skill when the task is about reviewing code changes, identifying risks, or generating review comments.
```

字段说明：

- `name`
  skill 名称，建议与目录名一致
- `description`
  一句话描述 skill 作用
- `triggers`
  用于自动匹配 task 的关键词
- `roles`
  给 planner / executor / reviewer 的角色级提示
- `references`
  可选补充材料
- `scripts`
  可选辅助脚本
- `allowed_tools`
  当前主要作为能力声明，后续可继续演进为动态工具过滤

## 执行链路

### model-backed 主路径

1. `ContextManager.prepare_role_context()` 只把紧凑 `skills_catalog` 注入 `context bundle`。
2. planner 先看到最小 catalog，可判断是否值得使用某个 skill。
3. executor 的 ReAct agent 会自行判断是否调用 `skill_list` / `skill_load`。
4. 推荐渐进顺序是：
   - `skill_list(role=<role>)`
   - `skill_load(name=<skill>, level="summary")`
   - `skill_load(name=<skill>, level="full")`
   - `skill_load(name=<skill>, level="reference", target="references/xxx.md")`
5. reviewer 只基于实际加载过的 skill 内容做校验，不假设未加载部分已经可见。

### deterministic fallback 路径

1. runtime 初始化时会根据 task 自动匹配 skill。
2. 若匹配到 skill，会自动在 pending tasks 前插入 `skill: <name>`。
3. 该步骤会通过 `skill_load` 预加载 skill 摘要。
4. 后续步骤继续走 fallback 的显式工具链或规则路由。

## 渐进式披露

当前支持以下层级：

- `summary`
  只加载 skill 元信息，不加载 `SKILL.md` 主体
- `full`
  加载 `SKILL.md` 主体
- `reference`
  精确加载某个 reference 文件
- `script`
  返回 skill 脚本路径，供后续执行链路消费

示例：

```bash
agentos skill-show code-review
agentos skill-show code-review --level full
agentos tool-run skill_list --arg role=executor
agentos tool-run skill_load --arg name=code-review --arg level=reference --arg target=references/checklist.md
```

## CLI 与工具入口

查看当前 skills：

```bash
agentos skill-list
```

查看某个 skill：

```bash
agentos skill-show code-review
agentos skill-show code-review --level full
```

也可以直接通过工具层调用：

```bash
agentos tool-run skill_load --arg name=code-review
agentos tool-run skill_list --arg role=executor
agentos tool-run skill_load --arg name=code-review --arg level=full
agentos tool-run skill_load --arg name=code-review --arg level=reference --arg target=references/checklist.md
```

## 模型路径验证

### 1. 准备 skill

确认存在：

```text
skills/code-review/SKILL.md
```

并且 `triggers` 中包含你将要测试的词，例如 `code review`。

### 2. 查看 skill 是否被发现

```bash
agentos skill-list
agentos skill-show code-review
```

### 3. 启动 model-backed shell

```bash
agentos shell --plain
```

### 4. 输入命中 skill 的自然语言任务

例如：

```text
请对当前仓库做 code review，重点关注潜在回归和测试缺失
```

预期行为：

- planner / executor / reviewer 能看到紧凑 `skills_catalog`
- executor 会自行决定是否先调用 `skill_list`，再进一步调用 `skill_load`
- 当需要更细规则时，模型可主动调用 `skill_load`

### 5. 验证 skill 是否实际进入链路

可以通过：

```bash
agentos session-show shell
```

检查：

- `context_bundle.skills_catalog`
- `context_bundle.matched_skills`
- `context_bundle.skills_hint`
- `tool_results`
  如果模型主动拉 deeper skill，里面会出现 `skill_list` 或 `skill_load`

一次已完成的验证样例：

- session: `shell2`
- turn: `.agentos/sessions/shell2/turn_0001.json`
- 证据：
  - `context_bundle.skills_catalog` 仅暴露最小 catalog
  - `tool_results` 中先出现 `skill_list`
  - 随后出现 `skill_load(level=summary)`

这说明模型路径已经按“最小 catalog -> 按需加载 skill”运行，而不是默认把 `SKILL.md` 正文塞进上下文。

## 示例 skill

仓库里建议放一个最小示例：

- `skills/code-review/SKILL.md`
- `skills/code-review/references/checklist.md`
- `skills/code-review/references/examples.md`
- `skills/code-review/scripts/gather_diff_context.py`

你可以直接复制这个结构继续扩展自己的 skill。
