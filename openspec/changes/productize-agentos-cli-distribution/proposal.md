## Why

当前 `agentOs` 已经具备可运行的交互式 agent shell，但仍然更像源码仓库而不是产品：启动依赖 `make`、`python -m` 和开发目录约定，安装后不能直接通过统一命令启动，终端表现也偏原始输出风格。下一条 change 需要把它收敛成“安装即可运行、交互界面更像产品”的 CLI 形态。

## What Changes

- 为 `agentOs` 增加标准 Python 打包入口，使用户可以通过 `pip install .`、`pip install -e .` 或 `pipx install .` 安装。
- 增加统一的 console script 命令 `agentos`，并让默认入口直接进入交互式 shell。
- 收敛 CLI 子命令结构，使最终用户命令面至少明确包含 `agentos`、`agentos shell`、`agentos run`、`agentos status`、`agentos session-show`、`agentos watch`，并符合产品使用习惯而不是开发期命令习惯。
- 增加首次配置与环境引导，包括 `.env.example`、缺失配置提示和最小启动文档。
- 提升终端交互表现层，使 shell 输出具备更清晰的用户区、agent 区、状态区、工具执行反馈和错误提示层级。
- 更新仓库文档与安装说明，使用户可以不依赖 `PYTHONPATH=src` 和 `make` 也能完成核心体验。

## Intended Final Shape

这条 change 完成后，`agentOs` 的终端产品形态需要明确为：

- 安装方式：
  - `pip install -e .`
  - 或 `pip install .`
  - 或 `pipx install .`
- 启动方式：
  - `agentos`
    - 默认直接进入常驻交互式 agent shell
  - `agentos shell`
    - 显式进入同一个交互式 shell
  - `agentos run "<task>"`
    - 一次性执行单条任务
  - `agentos status`
    - 查看当前配置、运行时和工作区状态
  - `agentos session-show <session-id>`
    - 查看指定会话历史与状态
  - `agentos watch <session-id>`
    - 持续观察指定会话的流转与更新

其中 `agentos` 和 `agentos shell` 必须成为主入口；`run/status/session-show/watch` 是围绕主入口配套的产品级辅助命令，而不是开发者内部命令。

## Capabilities

### New Capabilities
- `installable-python-distribution`: 定义 `agentOs` 作为可安装 Python CLI 产品的打包、安装和入口暴露行为。
- `packaged-cli-entrypoint`: 定义安装后通过 `agentos` 命令启动产品、默认进入交互 shell、并保留主要子命令的行为。
- `product-config-bootstrap`: 定义首次启动时的环境配置引导、`.env.example` 使用方式和缺失配置提示。
- `terminal-product-ui`: 定义终端产品界面的表现层，包括布局层级、流式反馈、状态展示和更清晰的交互输出风格。

### Modified Capabilities

## Impact

- 影响打包元数据、依赖声明、CLI 入口组织、README/安装说明、首次启动提示和终端输出表现层。
- 会新增 Python 包分发配置文件，并调整当前 `make`/`python -m` 风格入口与产品入口的关系。
- 不改变现有核心 runtime、tool、context、role workflow 的能力边界，重点是把现有能力暴露成可安装、可启动、可读性更好的产品形态。
