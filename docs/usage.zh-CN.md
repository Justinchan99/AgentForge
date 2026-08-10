# AgentForge 使用说明

[English](usage.md) | **简体中文**

AgentForge 分为两个作用范围：

- 每个操作系统用户安装一次 AgentForge。
- 每个需要使用该工作流的工程执行一次 `agentforge init`。该命令可以安全重复执行，只更新 AgentForge 管理的配置。

完整跨平台包从 `main` 获取（持续开发可使用 `develop`）。只需要 Linux 部署包时，可以克隆更精简的 `deploy` 分支：

```sh
git clone --branch deploy --single-branch https://github.com/Justinchan99/AgentForge.git
```

## 1. 安装 AgentForge

### Windows

在 AgentForge 源码目录执行：

```powershell
.\install.ps1
```

如果安装器将 `agentforge` 加入了 `PATH`，请重新打开一个 PowerShell 终端。

### Linux

```sh
chmod +x install.sh
./install.sh
```

如果当前 Shell 找不到 `agentforge`，请将用户级命令目录加入 `PATH`：

```sh
export PATH="$HOME/.local/bin:$PATH"
```

要永久生效，请将同一条命令写入相应的 Shell 配置文件，例如 `~/.bashrc` 或 `~/.zshrc`。

安装前，Linux 源码目录入口是 `./agentforge`；安装后使用 `PATH` 中的 `agentforge` 命令。

确认安装结果：

```sh
agentforge --version
agentforge doctor
```

## 2. 初始化工程

进入需要由 OpenCode 操作的工程根目录：

```sh
cd /path/to/project
```

先预览变更，不写文件也不安装依赖：

```sh
agentforge init --dry-run
```

初始化工程，并允许自动安装缺少的相关工具：

```sh
agentforge init --yes
```

如果依赖由其他方式管理，使用：

```sh
agentforge init --skip-install
```

初始化会创建或更新 `AGENTS.md` 中的受管理区块、`.agentforge/` 下的可移植策略、`.opencode/agents/` 下的真实 OpenCode Worker、工程级 OpenCode/LSP 配置以及 VS Code 扩展建议。

## 3. 启动 OpenCode

启动 OpenCode 时，应将已初始化工程作为项目上下文，以便加载 `AGENTS.md` 和 `.opencode/`。可以先进入工程目录：

```sh
cd /path/to/project
opencode
```

也可以直接传入工程路径：

```sh
opencode /path/to/project
```

当前 OpenCode 会话模型就是 Main Agent。AgentForge 不会创建名为 `main-agent` 的独立模型，因此 Agent 切换列表中不会出现该名称。

确认 OpenCode 已加载 Worker：

```sh
opencode agent list
```

输出中应包含 `deepseek-worker-free (subagent)`。不会出现单独的 `main-agent` 条目，这是正常现象。

`deepseek-worker-free` 被配置为 subagent，不会出现在 Tab 主 Agent 列表中。Main Agent 可以在适当时自动向它派发任务，也始终可以通过 `@` 手动调用：

```text
@deepseek-worker-free 搜索配置加载器并汇报实际调用路径
```

应当向 Worker 提供边界明确的执行任务。架构决策和最终验收由主会话负责。默认 Worker 可以编辑工程文件，运行 Shell 命令前会请求确认，不能继续创建 Agent，也不能访问工程目录以外的文件。

## 4. 启用可选 DeepSeek Worker

免费 Worker 不需要用户提供 DeepSeek API Key。可移植策略模板 `.agentforge/deepseek-worker.md` 始终生成，但只有 AgentForge 检测到 DeepSeek 认证后，才会创建或启用 OpenCode 实际加载的 `.opencode/agents/deepseek-worker.md`。

推荐使用 OpenCode 交互式认证：

```text
/connect
```

在 OpenCode 中选择 DeepSeek 并完成认证，然后重新初始化：

```sh
agentforge init
agentforge verify
```

也可以只通过当前 Shell 环境提供密钥：

```sh
export DEEPSEEK_API_KEY="..."
agentforge init
```

PowerShell：

```powershell
$env:DEEPSEEK_API_KEY="..."
agentforge init
```

切勿将 API Key 写入工程配置或提交到 Git。

完成认证后，可以向可选 Worker 派发边界明确的任务：

```text
@deepseek-worker 按批准的方案完成多文件修改并运行相关测试
```

## 5. 准备代码智能

对于需要编译数据库的 CMake 或 ROS 2 工程，执行：

```sh
agentforge prepare
```

`init` 不会启动大型构建。`prepare` 是生成 CMake 或 ROS 2 索引输入的显式步骤。如果工程根目录已经存在 `compile_commands.json`，AgentForge 会保留它。

## 6. 验证与诊断

初始化或环境变化后执行：

```sh
agentforge verify
```

输出 `READY` 表示必需的运行环境、Agent 策略、已配置 Worker、工程配置、模型目录项和相关 LSP 均可用。它不表示 Worker 已经完成真实任务，也不表示工程已经构建并通过测试。可选的 `deepseek-worker` 未启用不会导致验证失败。

看到 `READY` 后，在 OpenCode 中执行一个小型 Worker 冒烟任务：

```text
@deepseek-worker-free 列出工程顶层结构，不要修改文件
```

单独检查主机环境和工程识别结果：

```sh
agentforge doctor
```

## 7. 更新已有工程

首先更新 AgentForge 源码并重新安装用户级运行文件。

Linux：

```sh
cd /path/to/AgentForge
git pull
./install.sh
```

Windows：

```powershell
cd D:\path\to\AgentForge
git pull
.\install.ps1
```

然后在每个工程中重新执行：

```sh
cd /path/to/project
agentforge init
agentforge verify
```

AgentForge 只更新自己管理的 `AGENTS.md` 区块，保留用户已有 JSON 值；JSON 冲突需要安全备份时，只创建一次 `*.agentforge.bak`。

## Remote SSH

如果源码位于远程 Linux 主机，应在该 Linux 主机上安装和运行 AgentForge、OpenCode、语言服务器、构建和测试。本说明中的所有命令都应在 VS Code Remote SSH 终端执行。不要初始化一个仅用于显示远程文件的 Windows 本地目录。

## 常见问题

### PowerShell 命令没有输出

尚未安装时，如果直接从 Windows 源码目录运行，请使用 Windows 启动器：

```powershell
.\agentforge.cmd verify
.\agentforge.cmd doctor
```

无扩展名的 `./agentforge` 是 POSIX 启动器。安装完成后正常使用 `agentforge verify`。

### Tab 切换列表中没有 Worker

对于 `mode: subagent`，这是预期行为。请使用 `@deepseek-worker-free` 调用，或让 Main Agent 自动派发。初始化后应从工程根目录启动或重启 OpenCode。

### 可选 Worker 没有生成

完成 DeepSeek 认证后重新执行 `agentforge init`。认证前仍可使用 `deepseek-worker-free`。

### 没有配置 clangd 或 pyright

LSP 配置会按语言选择。只有检测到 C/C++ 源码时才配置 clangd，只有检测到 Python 源码时才配置 pyright。使用 `agentforge doctor` 检查语言识别结果。
