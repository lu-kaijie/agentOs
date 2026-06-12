# AgentOS 项目指令

## 技术栈

- Python 3.11+
- Textual TUI
- asyncio
- Pydantic
- Anthropic / OpenAI / OpenAI-compatible 模型服务
- MCP 工具接入

## 开发约定

- Commit message 使用英文。
- 变量名和函数名使用 `snake_case`。
- 优先使用明确的类型标注和现代 Python 语法。
- 工具执行、权限判断、UI 展示和模型调用要保持边界清晰。
- 用户可见的运行时名称统一为 `AgentOS`。
- Python 包名统一为 `agentos`。
- 项目运行状态统一放在 `.agentos/` 目录下。
