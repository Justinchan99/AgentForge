# AgentForge Linux 部署版

[English](README.md) | **简体中文**

本分支是 AgentForge 的最小 Linux 部署包。CLI、工程检测、Agent/LSP 配置、升级迁移、依赖安装、CMake/ROS 2 准备、验证逻辑和全部模板都包含在单个可执行文件 `agentforge` 中。

仓库仅包含：

```text
.gitattributes
LICENSE
README.md
README.zh-CN.md
agentforge
install.sh
```

`install.sh` 是面向尚未安装 Python 3.9 或更高版本机器的轻量引导脚本。Python 可用后，安装过程由自包含的 `agentforge` 脚本完成。

## 架构

```text
用户 -> Main Agent（当前 OpenCode 会话模型）
             |
             +--> deepseek-worker-free（默认 subagent）
             |    opencode/deepseek-v4-flash-free
             |
             `--> deepseek-worker（可选 subagent）
                  deepseek/deepseek-v4-pro
```

Main Agent 负责上下文、架构、规划、任务派发、审核和最终决策。Worker 负责执行边界明确的任务。

## 1. 每台 Linux 机器安装一次

```sh
git clone --branch deploy --single-branch https://github.com/Justinchan99/AgentForge.git
cd AgentForge
chmod +x install.sh agentforge
./install.sh
```

允许无提示安装缺少的依赖：

```sh
./install.sh --yes
```

如果 Python 3.9+ 和其他依赖由其他方式管理：

```sh
./install.sh --skip-tools
```

安装后的命令位于：

```text
~/.local/bin/agentforge
```

不再需要独立的 AgentForge 运行目录。升级时，会在新的单文件命令安装成功后安全清理旧版 `~/.local/share/agentforge`。

如果当前 Shell 找不到命令：

```sh
export PATH="$HOME/.local/bin:$PATH"
```

要永久生效，请将该命令写入 `~/.bashrc` 或 `~/.zshrc`。

确认安装结果：

```sh
agentforge --version
agentforge doctor
```

## 2. 初始化每个工程

每个 Linux 用户只需安装一次 AgentForge，但每个工程都要单独初始化。

```sh
cd /path/to/project
agentforge init --dry-run
agentforge init --yes
agentforge verify
```

- `--dry-run` 只预览变更，不写文件也不安装依赖。
- `--yes` 允许安装缺少的相关工具。
- `--skip-install` 只配置工程，不提示安装依赖。
- 重复执行 `init` 是安全且幂等的。

初始化会创建或更新：

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

## 3. 启动 OpenCode 并使用 Worker

启动 OpenCode 时，将已初始化工程作为项目上下文：

```sh
cd /path/to/project
opencode
```

或者：

```sh
opencode /path/to/project
```

检查加载的 Agent：

```sh
opencode agent list
```

输出中应包含 `deepseek-worker-free (subagent)`。当前会话模型就是 Main Agent，因此不会出现单独的 `main-agent` 条目。

subagent 不会出现在 Tab 主 Agent 列表中。Main Agent 可以自动派发，也可以直接调用：

```text
@deepseek-worker-free 搜索配置加载器并汇报实际调用路径
```

默认 Worker 可以编辑工程文件，运行 Shell 命令前会请求确认，不能继续创建 Agent，也不能访问工程目录以外的文件。

## 4. 启用可选 DeepSeek Worker

免费 Worker 不需要用户提供 DeepSeek Key。只有完成认证后，才会创建或启用真实的 `.opencode/agents/deepseek-worker.md`。

推荐使用 OpenCode 流程：

```text
/connect
```

选择 DeepSeek 并完成认证，然后执行：

```sh
agentforge init
agentforge verify
```

也可以只通过当前 Shell 环境提供密钥：

```sh
export DEEPSEEK_API_KEY="..."
agentforge init
```

切勿将 API Key 写入工程文件或提交到 Git。

## 5. CMake 和 ROS 2

`init` 只检测和配置，不会启动大型构建。需要编译数据库时显式执行：

```sh
agentforge prepare
```

工程根目录已有的 `compile_commands.json` 会被保留。ROS 2 环境必须先完成 source，确保 `colcon` 可用。

## 6. 验证和诊断

```sh
agentforge verify
agentforge doctor
```

`READY` 表示必需工具、Agent 策略、已配置 Worker、工程配置、模型目录项和相关 LSP 通过检查。它不表示 Worker 已完成真实任务，也不表示工程已经构建并通过测试。

看到 `READY` 后执行一个小型 Worker 冒烟任务：

```text
@deepseek-worker-free 列出工程顶层结构，不要修改文件
```

可选的 `deepseek-worker` 未启用不会导致验证失败。

## 7. 更新

```sh
cd /path/to/AgentForge
git pull
./install.sh
```

然后更新每个已初始化工程：

```sh
cd /path/to/project
agentforge init
agentforge verify
```

## Remote SSH

如果源码位于远程 Linux 主机，应通过 VS Code Remote SSH 终端在该主机上运行 AgentForge、OpenCode、语言服务器、构建和测试。不要初始化一个仅用于显示远程文件的 Windows 目录。

## 命令

```text
agentforge init [project] [--dry-run] [--yes] [--skip-install]
agentforge prepare [project] [--dry-run]
agentforge verify [project]
agentforge doctor [project]
```

## 安全策略

- `AGENTS.md` 受管理区块之外的现有内容会被保留。
- 现有 JSON 值优先；AgentForge 只添加缺失值。
- JSON 冲突会创建一次性 `*.agentforge.bak` 安全备份。
- 无效 JSON 和非 UTF-8 文件会被报告并保持不变。
- 只有精确匹配已知生成内容时，才迁移旧版 AgentForge 角色和全局 LSP 配置。
- `init` 不构建、不删除、不提交、不推送，也不修改工程源码。
- Worker 模板只包含模型 ID，不包含凭据。

## 常见问题

- Tab 中没有 Worker：对于 `mode: subagent` 这是预期行为；使用 `@deepseek-worker-free` 或让 Main Agent 自动派发。
- 可选 Worker 未生成：完成 DeepSeek 认证，然后重新执行 `agentforge init`。
- 没有 clangd 或 pyright：LSP 配置会按语言选择；使用 `agentforge doctor` 检查识别结果。
- 初始化后仍没有 Worker：以已初始化工程为项目上下文重启 OpenCode，并执行 `opencode agent list`。

## 许可证

MIT
