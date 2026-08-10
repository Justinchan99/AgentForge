# AgentForge Linux 使用说明

[English](usage.md) | **简体中文**

每个 Linux 用户只需安装一次 AgentForge。每个需要使用该工作流的工程都要单独执行 `agentforge init`。

## 1. 在 Linux 机器上安装

克隆部署分支并安装：

```sh
git clone --branch deploy --single-branch https://github.com/Justinchan99/AgentForge.git
cd AgentForge
chmod +x install.sh
./install.sh
```

如果当前 Shell 找不到 `agentforge`，执行：

```sh
export PATH="$HOME/.local/bin:$PATH"
```

要永久生效，请将该命令写入 `~/.bashrc` 或 `~/.zshrc`。安装前，源码目录入口是 `./agentforge`；安装后使用 `PATH` 中的 `agentforge`。

确认安装结果：

```sh
agentforge --version
agentforge doctor
```

## 2. 初始化每个工程

```sh
cd /path/to/project
agentforge init --dry-run
agentforge init --yes
```

dry run 只预览变更，不写文件也不安装依赖。如果主机依赖由其他方式管理，使用 `agentforge init --skip-install`。

初始化会管理 `AGENTS.md` 中的 AgentForge 区块、`.agentforge/` 中的可移植策略、`.opencode/agents/` 中的真实 OpenCode Worker、工程级 OpenCode/LSP 配置和 VS Code 扩展建议。

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

确认 Worker 配置：

```sh
opencode agent list
```

输出中应包含 `deepseek-worker-free (subagent)`。当前会话模型就是 Main Agent，因此不会出现单独的 `main-agent` 条目。

subagent 不会出现在 Tab 主 Agent 列表中。Main Agent 可以自动派发边界明确的工作，也可以直接调用免费 Worker：

```text
@deepseek-worker-free 搜索配置加载器并汇报实际调用路径
```

默认 Worker 可以编辑工程文件，运行 Shell 命令前会请求确认，不能继续创建 Agent，也不能访问工程目录以外的文件。架构决策和最终验收仍由主会话负责。

## 4. 启用可选 DeepSeek Worker

免费 Worker 不需要用户提供 DeepSeek Key。`.agentforge/deepseek-worker.md` 可移植模板始终生成，但只有完成认证后，才会创建或启用真实的 `.opencode/agents/deepseek-worker.md`。

推荐使用 OpenCode 交互式流程：

```text
/connect
```

选择 DeepSeek 并完成认证，然后执行：

```sh
agentforge init
agentforge verify
```

也可以在初始化前通过当前 Shell 环境提供密钥：

```sh
export DEEPSEEK_API_KEY="..."
agentforge init
```

切勿将 API Key 写入工程文件或提交到 Git。

## 5. 准备 CMake 或 ROS 2 索引

```sh
agentforge prepare
```

`init` 不会启动大型构建。`prepare` 用于显式生成 CMake 或 ROS 2 编译数据库输入。工程根目录已有的 `compile_commands.json` 会被保留。

## 6. 验证和冒烟测试

```sh
agentforge verify
agentforge doctor
```

`READY` 表示必需工具、Agent 策略、已配置 Worker、工程配置、模型目录项和相关 LSP 通过检查。它不表示 Worker 已执行真实任务，也不表示工程已构建并通过测试。

在 OpenCode 中执行一个小型 Worker 冒烟任务：

```text
@deepseek-worker-free 列出工程顶层结构，不要修改文件
```

可选的 `deepseek-worker` 未启用不会导致验证失败。

## 7. 更新 AgentForge

更新源码并重新安装用户级运行文件：

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

AgentForge 只更新自己管理的 `AGENTS.md` 区块，保留用户已有 JSON 值；JSON 冲突需要安全备份时，只创建一次 `*.agentforge.bak`。

## Remote SSH

如果源码位于远程 Linux 主机，应通过 VS Code Remote SSH 终端在该主机上运行 AgentForge、OpenCode、语言服务器、构建和测试。不要初始化一个仅用于显示远程文件的 Windows 目录。

## 常见问题

- Tab 中没有 Worker：对于 `mode: subagent` 这是预期行为；使用 `@deepseek-worker-free` 或让 Main Agent 自动派发。
- 可选 Worker 未生成：完成 DeepSeek 认证，然后重新执行 `agentforge init`。
- 没有 clangd 或 pyright：LSP 配置会按语言选择；使用 `agentforge doctor` 检查识别结果。
- 初始化后仍没有 Worker：以已初始化工程为项目上下文重启 OpenCode，并执行 `opencode agent list`。
