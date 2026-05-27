# agentOs 配置说明

## 基础配置

环境变量建议写到 `.env`：

```env
OPENAI_API_KEY=...
OPENAI_BASE_URL=...
```

完整模型相关配置示例：

```env
AGENTOS_MODEL_PROVIDER=openai
AGENTOS_MODEL_ENABLED=1
AGENTOS_CONTEXT_MODEL_COMPRESSION=0
AGENTOS_MEMORY_MODEL_EXTRACTION=1

AGENTOS_MODEL_SMALL=gpt-5.4
AGENTOS_MODEL_MEDIUM=gpt-5.4
AGENTOS_MODEL_LARGE=gpt-5.4

AGENTOS_PLANNER_MODEL_LEVEL=medium
AGENTOS_EXECUTOR_MODEL_LEVEL=medium
AGENTOS_REVIEWER_MODEL_LEVEL=medium

OPENAI_API_KEY=...
OPENAI_BASE_URL=...
```

## 三挡模型池

项目现在采用“三挡模型池 + role 选择档位”的方式配置模型。

```env
AGENTOS_MODEL_SMALL=gpt-5.4
AGENTOS_MODEL_MEDIUM=gpt-5.4
AGENTOS_MODEL_LARGE=gpt-5.4
```

默认 role 选择：

```env
AGENTOS_PLANNER_MODEL_LEVEL=medium
AGENTOS_EXECUTOR_MODEL_LEVEL=medium
AGENTOS_REVIEWER_MODEL_LEVEL=medium
```

含义：

- 先定义三挡模型池
- 各 role 只需要声明自己使用哪一挡
- 默认走 `medium`

## 上下文压缩配置

```env
AGENTOS_CONTEXT_MODEL_COMPRESSION=0
```

说明：

- `0` 表示只用启发式整理，不额外调用模型做压缩
- `1` 表示允许在长记忆压缩阶段调用模型生成更强语义摘要

## 结构化记忆抽取配置

```env
AGENTOS_MEMORY_MODEL_EXTRACTION=1
```

说明：

- `1` 表示允许在 turn 边界调用模型，通过结构化 tool/function output 生成 `MemoryDelta`
- 未配置模型、模型调用失败或返回不合法时，会记录诊断并回退到确定性抽取
- 结构化记忆会写入 `user_profile`、`remembered_facts`、`task_state` 等层
- 该开关不会让模型绕过工具或审批；文件、命令和测试仍通过运行时工具边界执行

## 常见建议

- 想先验证产品命令面，可先不开模型配置
- 想体验真实 agent 主路径，再补 `OPENAI_API_KEY` 和 `OPENAI_BASE_URL`
- 想体验 LLM 形成用户画像和事实记忆，打开 `AGENTOS_MEMORY_MODEL_EXTRACTION=1`
- 想减少成本或提高稳定性，可让某些 role 走 `small`
