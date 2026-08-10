# AgentForge

[English](README.md) | **简体中文**

AgentForge 是一个 OpenCode 多 Agent 工作流初始化工具。它不是 IDE，也不是一个新的 AI 编码 Agent。

它的核心原则很简单：

```text
高能力模型：思考、规划、决策
低成本 Worker：搜索、编辑、构建、测试
```

当前 OpenCode 会话所选模型继续担任 Main Agent。AgentForge 不会将其固定为 GPT、Claude、Gemini 或其他供应商模型。Main Agent 负责架构和最终决策，将边界明确的执行任务派发给 DeepSeek Worker，并审核执行结果。

```text
用户 -> Main Agent（当前会话模型）
              |
              +--> deepseek-worker-free（默认）
              |    opencode/deepseek-v4-flash-free
              |
              +--> deepseek-worker（可选）
                   deepseek/deepseek-v4-pro
              |
              v
         代码 / Shell / 测试 -> Main Agent 审核
```

## 配置内容

- 在 `AGENTS.md` 中写入受管理的工作流区块
- 与模型无关的 Main Agent 策略
- 将 `deepseek-worker-free` 配置为 OpenCode subagent
- 检测到 DeepSeek 认证时配置可选的 `deepseek-worker`
- 仅在检测到 C/C++ 源码时配置 clangd
- 仅在检测到 Python 源码时配置 pyright
- VS Code 语言支持和 Remote SSH 扩展建议
- 安全、增量地合并 OpenCode JSON 配置
- 准备 CMake 和 ROS 2 编译数据库

Agent Markdown 使用 OpenCode 的工程级 `.opencode/agents/` 格式。Worker 模型 ID 来自当前 OpenCode/Models.dev 模型目录，不使用虚构的配置字段。

## Linux 部署

CLI 要求 Python 3.9 或更高版本。安装器会检测现有工具，只安装缺少的组件。AgentForge 不会请求、打印或写入 API Key。

```sh
git clone --branch deploy --single-branch <agentforge-repository>
cd AgentForge
chmod +x install.sh
./install.sh

cd /path/to/project
agentforge init
agentforge verify
```

安装器支持 Ubuntu/Debian 的 `apt-get` 和 Fedora 系列的 `dnf`。可以检测 x86_64 和 ARM64，实际软件包可用性取决于发行版仓库。

### Remote SSH Linux

在源码实际所在的远程 Linux 终端中安装和运行 AgentForge：

```sh
# Linux 主机上的 VS Code Remote SSH 终端
git clone --branch deploy --single-branch <agentforge-repository>
cd AgentForge
./install.sh

cd /remote/path/to/project
agentforge init
agentforge verify
```

OpenCode、Worker、clangd/pyright、构建、测试和代码库均位于 Linux。Windows 负责 VS Code 界面、Remote SSH、Git 界面和用户交互。不要使用 Windows 本机的 clangd 分析远程 Linux 工程。

## 命令

```text
agentforge init [project] [--dry-run] [--yes] [--skip-install]
agentforge prepare [project] [--dry-run]
agentforge verify [project]
agentforge doctor [project]
```

- `init` 检测工程、提示安装缺少的相关依赖，并安全配置 Agent 和 LSP；不会构建工程。
- `prepare` 配置 CMake，或按需准备 ROS 2 编译数据库输入。
- `verify` 检查 OpenCode、Main Agent 策略、Worker、相关 LSP、构建工具和 AGENTS 工作流区块。
- `doctor` 输出主机、运行模式、架构、工具、语言、CMake 和 ROS 2 的详细检测结果。

`init --dry-run` 不写入文件，也不安装工具。

## Agent 行为

### Main Agent

Main Agent 不是单独固定的模型。当前会话模型读取注入的工作流，并负责：

- 理解需求和维护会话上下文
- 推理、架构和规划
- 拆分任务并选择 Worker
- 审核 Worker 结果、决定是否重试并作出最终决策

### deepseek-worker-free

始终配置为可见的 `mode: subagent`，使用：

```yaml
model: opencode/deepseek-v4-flash-free
```

适用于搜索、小范围修改、重复编辑、测试、构建、日志分析和简单调试。

### deepseek-worker

仅当 AgentForge 检测到 `DEEPSEEK_API_KEY` 或 `opencode auth list` 中已有 DeepSeek 凭据时，才会在 `.opencode/agents/` 中配置：

```yaml
model: deepseek/deepseek-v4-pro
```

请通过 OpenCode 的 `/connect` 流程安全认证，或者在运行 `agentforge init` 前在 Shell 中设置 `DEEPSEEK_API_KEY`。没有认证时，初始化仍会成功，并将该 API Worker 报告为可选且不可用。

切勿提交 API Key。AgentForge 会为本地密钥文件和 `*.agentforge.bak` 配置忽略规则。

## 生成文件

```text
project/
|-- AGENTS.md
|-- .gitignore
|-- .agentforge/
|   |-- .gitignore
|   |-- main-agent.md
|   |-- deepseek-worker-free.md
|   `-- deepseek-worker.md
|-- .opencode/
|   |-- opencode.json
|   `-- agents/
|       |-- deepseek-worker-free.md
|       `-- deepseek-worker.md      # 仅在有 DeepSeek 认证时生成
`-- .vscode/
    |-- settings.json
    `-- extensions.json
```

`.agentforge/` 保存可移植策略模板；`.opencode/agents/` 才是 OpenCode 实际加载的目录。

## 安全与幂等性

- `AGENTS.md` 中 `<!-- AGENTFORGE:BEGIN -->` / `<!-- AGENTFORGE:END -->` 以外的现有内容保持字节级不变。
- 后续更新只替换 AgentForge 管理的区块。
- 现有 JSON 值优先；AgentForge 只添加缺失值。
- 配置冲突时，合并前创建一次性 `*.agentforge.bak`。
- 遇到无效 JSON 或非 UTF-8 文件时报告问题，并保持原文件不变。
- Worker/API 模板只包含模型 ID，不包含凭据。
- `init` 不构建、不删除、不提交、不推送，也不修改业务源码。
- 重复初始化具有幂等性。

## CMake 和 ROS 2

`agentforge init` 只检测和配置，不会启动大型构建。

对于 CMake 工程：

```sh
agentforge prepare
```

该命令在 `.agentforge/cmake-build` 下执行 CMake 配置，并启用 `CMAKE_EXPORT_COMPILE_COMMANDS=ON`。对于 ROS 2，`prepare` 使用受管理的 colcon build/install/log 目录，并在 `.agentforge` 下合并各软件包的编译数据库。

如果工程根目录已有 `compile_commands.json`，AgentForge 会保留并直接使用它。

更多信息请参阅[架构说明](docs/architecture.md)、[Linux](docs/linux.md)和[Remote SSH](docs/remote-ssh.md)。

## 许可证

MIT
