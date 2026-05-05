# agentOs 产品化验收清单

## 安装验证

```bash
python3 -m venv .venv-agentos
source .venv-agentos/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m pip install -e .
```

确认以下命令可执行：

```bash
agentos status
agentos --help
```

## 启动验证

1. 执行 `agentos`
2. 确认默认进入常驻 shell，而不是只打印帮助
3. 如果模型未配置，确认会看到 `.env.example` 与 `OPENAI_API_KEY` 的引导
4. 如果模型已配置，确认可以直接输入自然语言任务
5. 如果要验证语义记忆的模型压缩路径，显式设置 `AGENTOS_CONTEXT_MODEL_COMPRESSION=1`

## 命令面验证

逐个验证以下命令存在且行为正确：

```bash
agentos
agentos shell
agentos run "阅读 README.md 并总结当前项目状态" --model
agentos status
agentos session-show shell
agentos watch shell
```

## 界面验证

在支持 TTY 的终端中：

1. 执行 `agentos`
2. 确认界面存在稳定的状态区、活动区和输入区
3. 提交一个任务，确认用户输入、agent 输出、工具活动与错误信息可区分
4. 执行 `/status`，确认可查看当前 session 状态

如果当前环境不支持 `textual` 或不是 TTY：

1. 执行 `agentos shell --plain`
2. 确认仍能稳定进入 plain shell
3. 确认 banner、状态输出和最终回答可读

## 长会话上下文验证

1. 执行 `agentos shell --plain --session-id context-demo`
2. 连续输入多轮任务，至少覆盖：
   - 普通自然语言请求
   - 文件读取或搜索
   - 一次测试或命令执行
   - 一次失败场景
3. 执行 `agentos session-show context-demo`
4. 确认输出里存在：
   - `memory_state`
   - `working_memory`
   - `tool_facts`
   - `failure_memory`
   - `lifecycle_audits`
5. 确认 session 恢复后这些结构化字段仍然可见

## 回归验证

```bash
make test
```

重点关注：

- `agentos` 无参默认入口
- `run/status/session-show/watch` 命令仍可用
- 未配置模型时的提示是否仍然清晰
- 安装后不再依赖 `PYTHONPATH=src`
