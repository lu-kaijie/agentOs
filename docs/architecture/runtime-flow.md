# 运行链路

如果你想看结合代码、按函数名展开的详细版，请先读：

- [持续交互主链路详解](interactive-mainline-deep-dive.md)

## 交互式 shell 主链路

当你执行 `agentos` 时，主链路大致是：

1. CLI 入口解析参数
2. 进入 shell presentation
3. 接收用户输入
4. 把输入交给 runtime
5. runtime 组装 context bundle
6. 进入 LangGraph role / tool / review 流程
7. 持久化 session 和记忆
8. 把结果回显给用户

## one-shot `run` 主链路

当你执行 `agentos run "<task>" --model` 时：

1. CLI 构造 runtime 请求
2. runtime 加载 session 和上下文
3. planner 先决定任务拆解或执行方向
4. executor 调用工具或直接生成回答
5. reviewer 做收尾和检查
6. 最终结果回到 CLI 输出

## `watch` 主链路

当你执行 `agentos watch <session>` 时：

1. 轮询 session 状态
2. 检查是否有新 turn 或状态变化
3. 展示最新执行情况

当前 `watch` 是轮询式，不是主动推送式。
