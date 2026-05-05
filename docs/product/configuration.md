# agentOs 配置说明

## 基础配置

环境变量建议写到 `.env`：

```env
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

## 常见建议

- 想先验证产品命令面，可先不开模型配置
- 想体验真实 agent 主路径，再补 `OPENAI_API_KEY` 和 `OPENAI_BASE_URL`
- 想减少成本或提高稳定性，可让某些 role 走 `small`
