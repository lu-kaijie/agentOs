## Context

当前 `agentOs` 已经有稳定的 CLI、真实模型主路径、常驻 shell、LangChain-native tools 和会话持久化能力，但这些能力仍然建立在开发者工作流上：运行时默认依赖源码目录、`PYTHONPATH=src`、虚拟环境路径和 `make` 包装命令。对于“像产品一样安装后直接启动”的目标，这一层已经成为主要缺口。

这条 change 的重点不是新增 agent 能力，而是把现有能力重新包装成标准 Python CLI 产品入口，并确保首次安装、首次启动和终端交互表现都足够接近产品形态。

## Goals / Non-Goals

**Goals:**
- 让用户可以通过标准 Python 打包方式安装 `agentOs`。
- 提供统一 console script：`agentos`。
- 让 `agentos` 默认进入交互式 shell，使产品主入口和主体验保持一致。
- 保留并明确产品级命令面：`agentos`、`agentos shell`、`agentos run`、`agentos status`、`agentos session-show`、`agentos watch`。
- 为首次使用者提供最小配置引导，包括 `.env.example` 和缺失配置提示。
- 改善终端表现层，让 shell 输出比当前原始 CLI 更有层级和稳定布局。
- 让 README 的安装和使用说明以“安装后直接命令启动”为主，而不是以开发命令为主。

**Non-Goals:**
- 这条 change 不重写当前 runtime、role、tool 或 context 架构。
- 不引入 GUI / Web UI。
- 不处理 PyPI 正式发布、签名分发或跨平台打包二进制。
- 不在这条 change 中重做复杂图形界面系统或主题系统。

## Decisions

### 1. 使用标准 Python 打包元数据，而不是继续只靠 requirements + PYTHONPATH

采用 `pyproject.toml` 作为产品化入口，定义项目元数据、依赖和 console script。

理由：
- 这是 `pip install .` / `pipx install .` 的标准路径。
- 可以消除“必须从源码目录用 `python -m` 启动”的限制。

备选方案：
- 继续只维护 `requirements.txt` 和 `make`。放弃，因为这只能服务开发者，不能满足产品入口目标。

### 2. `agentos` 默认进入 shell，而不是只显示帮助

安装后的主命令 `agentos` 直接进入交互式 shell；同时保留 `agentos shell` 作为显式别名。

理由：
- 你要求“像产品一样安装后通过命令启动”，默认进入产品主界面最符合这个预期。
- 当前项目的核心体验已经是常驻 shell，而不是一次性子命令。

备选方案：
- `agentos` 默认显示帮助，必须 `agentos shell` 才进入主界面。放弃，因为这会增加一次多余操作。

### 2.1 产品命令面必须固定，而不是边做边决定

这一条 change 完成后，最终面向用户的主命令面至少应稳定包含：
- `agentos`
- `agentos shell`
- `agentos run`
- `agentos status`
- `agentos session-show`
- `agentos watch`

理由：
- 你已经明确希望它“安装后通过命令启动”，这要求命令面本身成为产品契约。
- `session-show` 和 `watch` 对这个项目尤其重要，因为它们直接承接了现有的可观察性和持续工作流能力。

进一步明确每个命令的职责：
- `agentos`
  - 默认进入常驻交互式 shell，是产品主入口
- `agentos shell`
  - 进入同一个 shell，用于显式表达“我要进入交互模式”
- `agentos run`
  - 适合脚本化、单次执行、自动化测试或快速试跑
- `agentos status`
  - 展示模型配置、工作区、当前 runtime 状态等摘要信息
- `agentos session-show`
  - 面向会话排查、复盘和历史检查
- `agentos watch`
  - 面向持续观察某个会话的进度变化，而不是重新进入 shell

### 3. 首次配置失败时给明确引导，而不是直接让底层异常暴露

当模型配置缺失或 `.env` 未准备好时，CLI 应给出清晰提示，引导用户复制 `.env.example` 并填写必要变量。

理由：
- 产品入口的失败提示必须面向用户，而不是面向源码调试。
- 当前 `.env.example` 已经存在，适合成为统一引导入口。

### 4. 保留开发命令，但 README 主叙事切换为产品命令

`make` 和 `python -m` 仍可保留给开发者，但 README 和主要说明应优先展示：
- `pip install -e .`
- `agentos`
- `agentos run`

理由：
- 不打断现有开发工作流。
- 同时让用户看到正确的产品使用方式。

### 5. 终端美化限定在产品级 TUI/CLI 表现，而不是 Web UI

终端表现层应优先采用 `textual`，次选才是 `rich` / `prompt_toolkit` 这类终端友好方案。第一版至少做到：
- 用户输入、agent 输出、工具执行、错误提示分层
- 稳定的状态区或摘要区
- 更清晰的流式反馈与长输出展示
- 固定输入区，而不是纯 `prompt + print` 混排
- 启动后更像产品化 TUI，而不是脚本式滚动输出

第一版可以接受的界面形态是：
- 顶部：标题和会话状态栏
- 中间主区：对话流 / 工具活动流
- 底部：固定输入框
- 可选侧栏或底部摘要区：当前模型、session id、审批状态、最近工具动作

也就是说，这条 change 的目标不是“打印更好看一点”，而是形成一个稳定、连续、安装后可直接进入的终端产品界面。

理由：
- 你的目标是“像产品一样的命令行工具”，不是浏览器界面。
- 你已经明确提到希望更像 Claude Code 一样的产品，`textual` 更容易给出稳定布局和产品感。

备选方案：
- 只做 `rich` 美化但不引入固定布局。降级备选，仅当 `textual` 实现成本明显超出本条 change 预算时才考虑。
- 直接引入 Web UI。放弃，因为这会把范围从 CLI 产品化扩展成另一条产品线。

## Risks / Trade-offs

- [打包入口引入新的元数据维护成本] → Mitigation：保持 `pyproject.toml` 最小化，只先覆盖当前运行所需依赖和 console script。
- [默认 `agentos` 直接进 shell 可能让部分用户意外] → Mitigation：保留 `agentos --help`、`agentos shell` 和清晰 README 说明。
- [首次配置提示如果处理不当会和现有异常流重复] → Mitigation：只在最常见的缺失配置路径上做用户友好提示，不吞掉实际运行错误。
- [开发入口和产品入口并存可能造成文档混乱] → Mitigation：README 明确区分“产品使用”和“开发调试”。
- [终端美化如果做得过重，可能拖慢产品化交付] → Mitigation：第一版优先做产品级固定布局和状态区，不在这一条 change 中追求过多主题、动画或复杂面板系统。

## Migration Plan

1. 增加标准 Python 打包文件和 console script。
2. 调整 CLI 主入口，使 `agentos` 默认进入 shell。
3. 补齐首次配置提示和 `.env.example` 文档说明。
4. 引入终端产品表现层的最小增强。
5. 更新 README 和安装使用说明。
6. 增加安装后 smoke test，验证 `agentos --help` 或 `agentos status` 能正常执行。

## Open Questions

- 是否在这条 change 中同时加入 `agentos init`，还是先只靠 `.env.example` 和错误提示？
- 是否需要把当前版本号从源码常量迁移到打包元数据统一管理？
- `textual` 第一版布局是否采用“顶部状态栏 + 中间对话流 + 底部输入框 + 右侧活动栏”的四区结构？
