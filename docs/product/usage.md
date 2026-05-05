# agentOs 详细使用

## 交互式 shell

默认启动：

```bash
agentos
```

显式启动：

```bash
agentos shell
```

如果你想强制 plain shell：

```bash
agentos shell --plain
```

如果你想强制 Textual TUI：

```bash
agentos shell --tui
```

shell 内常用交互：

- 直接输入自然语言任务
- `/status` 查看当前 session 状态
- `/exit` 退出当前 shell

## 单轮执行

适合脚本化或快速试跑：

```bash
agentos run "请读取 README.md，并用两句话总结这个项目"
agentos run "请读取 README.md，并用两句话总结这个项目" --model
```

## 状态查看

查看当前环境和 runtime 状态：

```bash
agentos status
```

查看某个 session：

```bash
agentos session-show shell
```

持续观察某个 session：

```bash
agentos watch shell
```

## 工具能力

查看可用工具：

```bash
agentos tool-list
```

手动执行单个工具：

```bash
agentos tool-run file_read --arg path=README.md
agentos tool-run repo_search --arg query=context
```

## 非模型 fallback

如果没有配置模型，系统会退回 deterministic 路径。你仍然可以执行显式任务 DSL：

```bash
agentos run "code: steps: read: README.md | write: notes.txt => demo | test: python -c print(123)"
```
