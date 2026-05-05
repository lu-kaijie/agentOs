# agentOs 快速上手

## 1. 安装

```bash
python3 -m venv .venv-agentos
source .venv-agentos/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m pip install -e .
```

## 2. 准备配置

```bash
cp .env.example .env
```

至少填写：

```env
OPENAI_API_KEY=...
OPENAI_BASE_URL=...
```

## 3. 直接启动

```bash
agentos
```

这会默认进入交互式 shell。

## 4. 第一轮体验

进入 shell 后，可以直接输入：

```text
请先阅读 README.md，然后总结这个项目当前处于什么阶段
搜索 tests 里和 context 相关的测试
运行测试并告诉我结果
```

## 5. 常用命令

```bash
agentos
agentos shell
agentos run "请读取 README.md 并总结当前项目状态" --model
agentos status
agentos session-show shell
agentos watch shell
```
