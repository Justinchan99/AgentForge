你需要设计并实现一个开源项目：

# AgentForge

AgentForge 是一个“一键配置 AI 多 Agent 协同开发环境”的初始化工具。

用户只需要在任意代码工程根目录运行一次初始化命令，即可完成：

- opencode 工程配置
- 主 Agent / 子 Agent 协同工作流配置
- DeepSeek Worker 配置
- LSP 配置
- AGENTS.md 工作流注入
- C/C++ / Python 代码智能支持
- Windows / Linux 跨平台适配
- Windows + SSH Remote Linux 开发适配
- VS Code 协同开发环境适配

最终形成：

当前对话模型作为 Main Agent
+
DeepSeek Worker 子 Agent
+
LSP
+
VS Code
+
opencode

组成的 AI 协同软件开发工作流。


==================================================
一、核心设计原则
==================================================

AgentForge 的核心不是固定多个角色模型，而是：

“主 Agent 负责思考和调度，便宜的子 Agent 负责执行。”

主 Agent 一般直接继承用户当前 opencode 对话所使用的模型。

例如：

GPT
Claude
Gemini
其他高能力模型

都可以作为 Main Agent。

AgentForge 不应把 Main Agent 写死为某一个具体模型。


整体架构：

                User
                  |
                  |
          VS Code / opencode
                  |
                  |
             Main Agent
       当前对话所使用的模型
                  |
        需求理解 / 推理 / 规划
                  |
             Task Dispatch
                  |
        -----------------------
        |                     |
        ↓                     ↓
DeepSeek Worker Free    DeepSeek Worker API
        |                     |
DeepSeek V4 Flash       DeepSeek V4
Free                    User API Key
        |                     |
        ---------+-----------
                 |
                 ↓
          Code / Shell / Test
                 |
                 ↓
               LSP
                 |
        -------------------
        |                 |
      clangd           pyright
        |                 |
        ------ Codebase ----


==================================================
二、Agent职责划分
==================================================


--------------------------------------------------
1. Main Agent
--------------------------------------------------

Main Agent 不绑定具体模型。

Main Agent 默认就是：

“当前 opencode 主对话所使用的模型”。

Main Agent 是整个工作流的控制器。


职责：

- 理解用户需求
- 读取已有对话上下文
- 分析工程结构
- 做技术方案设计
- 做架构决策
- 将复杂需求拆解为可执行任务
- 决定哪些工作自己完成
- 决定哪些工作委派给子 Agent
- 为子 Agent 编写明确任务描述
- 接收子 Agent 执行结果
- 检查结果
- 必要时重新派发修复任务
- 最终向用户汇总结果


Main Agent 应尽量避免：

- 自己执行大量机械性文件修改
- 自己处理大量重复代码编辑
- 自己执行大量简单 Shell 命令
- 为低价值执行任务消耗昂贵模型 token


Main Agent 应优先承担：

Reasoning
Planning
Architecture
Task decomposition
Review
Decision making


--------------------------------------------------
2. DeepSeek Worker Free
--------------------------------------------------

Agent 名称建议：

deepseek-worker-free


模型：

opencode 自带的：

DeepSeek V4 Flash Free


特点：

- 免费
- 适合大量简单执行任务
- 适合代码搜索
- 适合读取文件
- 适合小范围代码修改
- 适合生成样板代码
- 适合执行命令
- 适合编译测试
- 适合日志分析
- 适合格式化、重命名等机械任务


Main Agent 应优先将低风险、低复杂度任务派给该 Worker。


例如：

- 查找函数定义
- 搜索调用关系
- 修改简单配置
- 创建测试代码
- 修复简单编译错误
- 执行 build
- 执行 test
- 分析日志
- 修改重复性代码


--------------------------------------------------
3. DeepSeek Worker API
--------------------------------------------------

Agent 名称建议：

deepseek-worker


模型：

DeepSeek V4


Provider：

由用户提供 API Key。


特点：

- 相比 Free Worker 可承担更复杂执行任务
- 适合较大范围代码修改
- 适合多文件实现
- 适合复杂调试
- 适合根据详细方案完成模块开发


使用场景：

当：

deepseek-worker-free

能力不足，或者任务复杂度较高时，

Main Agent 可以将任务派发给：

deepseek-worker


注意：

AgentForge 不应把用户 API Key 写入仓库。

必须使用：

环境变量

或者：

opencode 官方支持的安全配置方式。


初始化过程中：

如果未发现 DeepSeek API Key：

仍然允许 AgentForge 正常工作。

此时：

deepseek-worker-free

仍然可用。

deepseek-worker

应标记为：

Optional / Not Configured


==================================================
三、Agent调度原则
==================================================


Main Agent 应按照以下策略选择 Worker：


优先级 1：

deepseek-worker-free


适用于：

- 简单任务
- 机械任务
- 搜索任务
- 小规模修改
- 编译测试
- 日志分析


如果 Free Worker：

- 执行失败
- 无法完成任务
- 输出质量不足
- 任务本身复杂度较高


则 Main Agent 可以选择：


优先级 2：

deepseek-worker


适用于：

- 多文件修改
- 较复杂功能开发
- 较复杂 Debug
- 大范围重构
- 根据架构方案实现完整模块


如果任务涉及：

重大架构决策
复杂算法设计
关键接口变更
系统设计


仍应由：

Main Agent

完成决策。

Worker 主要负责：

执行。


==================================================
四、标准工作流
==================================================


标准流程：


User

↓

Main Agent

↓

理解需求和现有对话上下文

↓

分析代码工程

↓

制定方案

↓

拆分任务

↓

选择 Worker

↓

优先：

deepseek-worker-free

↓

必要时：

deepseek-worker

↓

Worker 执行：

- 阅读代码
- 修改文件
- 执行命令
- 编译
- 测试

↓

返回结果给 Main Agent

↓

Main Agent Review

↓

如果失败：

重新派发任务

↓

如果成功：

Main Agent 汇总结果

↓

User


必须明确：

子 Agent 不应该自行改变总体架构方案。

如果发现方案存在问题：

Worker 应向 Main Agent 报告。

最终决策仍由 Main Agent 完成。


==================================================
五、开发环境组成
==================================================


VS Code：

主要负责：

- 代码浏览
- 文件编辑
- Git 图形化管理
- Debug
- Remote SSH
- Extensions
- 工程管理


opencode：

主要负责：

- Main Agent 对话
- Agent 调度
- Worker执行
- AI代码修改
- Shell工具调用


LSP：

主要负责：

- 代码语义理解
- 定义跳转
- References
- Diagnostics
- Symbol
- Type information


C/C++：

clangd


Python：

pyright


==================================================
六、支持三种运行模式
==================================================


必须支持以下三种环境。


--------------------------------------------------
Mode A
Windows 本地开发
--------------------------------------------------


场景：

Windows

├── VS Code
├── opencode
├── AgentForge
└── Local Project


检查：

- git
- node
- npm
- opencode
- clangd
- pyright
- cmake
- ninja


只安装缺失组件。


配置：

Main Agent：

继承当前对话模型。


Worker：

deepseek-worker-free

默认启用。


Worker：

deepseek-worker

如果检测到 DeepSeek API Key，则配置。


--------------------------------------------------
Mode B
Windows + SSH Remote Linux
--------------------------------------------------


推荐架构：

Windows

VS Code

      |
      | Remote SSH
      ↓

Linux Remote Host

├── Project
├── opencode
├── AgentForge
├── clangd
├── pyright
└── build environment


原则：

AI Agent 与 LSP 应尽可能运行在：

“实际代码所在的 Linux 主机”。


不要让 Windows 本机的 clangd 去分析远程 Linux 工程。


在 Remote Linux：

自动检查：

- opencode
- git
- clangd
- pyright
- cmake
- ninja
- node/npm


并完成：

AgentForge 项目初始化。


Windows 端主要负责：

- VS Code
- Remote SSH
- Git UI
- 用户交互


Linux Remote 负责：

- Agent
- Worker
- LSP
- Build
- Test
- Codebase


--------------------------------------------------
Mode C
Linux 本地开发
--------------------------------------------------


Linux

├── VS Code
├── opencode
├── AgentForge
├── clangd
├── pyright
└── Project


自动完成全部环境检查和初始化。


必须兼容：

x86_64 Linux

ARM64 Linux


==================================================
七、仓库结构
==================================================


建议生成：


AgentForge/
│
├── install.ps1
├── install.sh
├── README.md
├── LICENSE
│
├── scripts/
│   ├── detect_environment.py
│   ├── configure_project.py
│   ├── configure_agents.py
│   ├── configure_lsp.py
│   ├── configure_agents_md.py
│   ├── verify.py
│   ├── install_windows.ps1
│   └── install_linux.sh
│
├── templates/
│   ├── opencode.json
│   ├── AGENTS.md
│   ├── main-agent.md
│   ├── deepseek-worker-free.md
│   └── deepseek-worker.md
│
└── docs/
    ├── architecture.md
    ├── windows.md
    ├── linux.md
    └── remote-ssh.md


==================================================
八、一键使用方式
==================================================


最终用户体验应尽量压缩。


Windows：


进入用户自己的工程：


cd path\to\project


执行：

agentforge init


或者首次安装时：

PowerShell：

.\install.ps1


之后：

agentforge init


--------------------------------------------------


Linux：


cd /path/to/project


执行：

agentforge init


首次安装：

./install.sh


==================================================
九、自动环境检测
==================================================


运行：

agentforge init


首先输出类似：


AgentForge

Environment:

OS:
Windows 11

Architecture:
x86_64

Development Mode:
Windows Local


Tools:

✓ git
✓ opencode
✓ node
✓ npm

✗ clangd
✗ pyright

Installing missing dependencies...


Agents:

✓ Main Agent
  inherited from current conversation

✓ deepseek-worker-free
  DeepSeek V4 Flash Free

○ deepseek-worker
  DeepSeek V4
  API key not configured


LSP:

✓ clangd
✓ pyright


Project:

CMake project detected


Status:

READY


==================================================
十、AGENTS.md 配置
==================================================


这是 AgentForge 的核心功能之一。


初始化时：

检查当前工程根目录：

AGENTS.md


--------------------------------------------------
情况 A：
不存在 AGENTS.md
--------------------------------------------------


创建：

AGENTS.md


写入完整 AgentForge 工作流描述。


至少包含：


# AgentForge Workflow


## Architecture


This project uses the AgentForge hierarchical multi-agent development workflow.


Main Agent:

The Main Agent inherits the model used by the current opencode conversation.

Responsibilities:

- understand user requirements
- maintain conversation context
- analyze architecture
- plan implementation
- decompose tasks
- dispatch tasks to worker agents
- review worker results
- make final technical decisions


Worker Agents:


### deepseek-worker-free

Model:

DeepSeek V4 Flash Free

Purpose:

Low-cost execution worker.

Use for:

- code search
- small modifications
- repetitive editing
- build
- test
- log analysis
- simple debugging


### deepseek-worker

Model:

DeepSeek V4

Authentication:

User-provided API key.

Purpose:

Higher-capability execution worker.

Use for:

- multi-file implementation
- complex code changes
- larger debugging tasks
- implementation based on Main Agent architecture


## Dispatch Policy


Main Agent should:

1. Analyze the task.

2. Keep architecture and reasoning responsibilities.

3. Delegate execution-heavy tasks.

4. Prefer deepseek-worker-free when possible.

5. Escalate to deepseek-worker when the free worker is insufficient.

6. Review worker results before accepting changes.

7. Run build/tests when applicable.


Workers should not make major architecture decisions independently.


## Development Tools


VS Code:

IDE / Git / Debug / Remote SSH


opencode:

Main Agent and worker orchestration


LSP:

clangd for C/C++

pyright for Python


--------------------------------------------------
情况 B：
已经存在 AGENTS.md
--------------------------------------------------


绝对不能覆盖已有内容。


在：

AGENTS.md

文件最顶部追加：

AgentForge 工作流说明。


必须包含唯一标识：


<!-- AGENTFORGE:BEGIN -->


和：


<!-- AGENTFORGE:END -->


例如：


<!-- AGENTFORGE:BEGIN -->

# AgentForge Workflow

This project uses a hierarchical multi-agent workflow.

Main Agent:
- inherits the current conversation model
- handles reasoning, architecture and task decomposition
- dispatches execution tasks to workers
- reviews results

Workers:

deepseek-worker-free:
- DeepSeek V4 Flash Free
- default low-cost execution worker

deepseek-worker:
- DeepSeek V4
- optional
- uses user-provided API key
- handles more complex implementation tasks

Dispatch policy:

Main Agent → deepseek-worker-free → deepseek-worker when necessary.

Workers execute.
Main Agent decides.

Tools:

- opencode
- VS Code
- clangd
- pyright

<!-- AGENTFORGE:END -->


然后保留用户原有：

AGENTS.md

全部内容。


要求：

重复执行：

agentforge init

时：

检测：

AGENTFORGE:BEGIN

如果已经存在：

不要再次追加。


未来 AgentForge 更新配置时：

只允许更新：

AGENTFORGE:BEGIN

到：

AGENTFORGE:END

之间的内容。

不得修改其他内容。


==================================================
十一、Agent配置
==================================================


根据当前 opencode 实际支持的 Agent 配置方式实现。


不要假设不存在的配置格式。

应优先读取当前 opencode 配置。


配置目标：


Main Agent：

不绑定模型。

继承当前 session / conversation model。


创建两个可调用子 Agent：


1.

deepseek-worker-free


模型：

opencode 当前提供的：

DeepSeek V4 Flash Free


2.

deepseek-worker


模型：

DeepSeek V4


Provider：

DeepSeek API


认证：

由用户 API Key 提供。


如果 API Key 不存在：

不要报错退出。

只提示：

deepseek-worker unavailable

deepseek-worker-free remains available.


==================================================
十二、API Key安全要求
==================================================


绝对禁止：

把 API Key：

写入：

- Git仓库
- AGENTS.md
- README
- 模板文件
- 明文项目配置


优先使用：

环境变量

或者：

opencode 官方认证机制。


.gitignore

必须自动确保忽略：

可能包含 secret 的 AgentForge 本地配置。


==================================================
十三、LSP
==================================================


自动检测工程语言。


如果存在：

.cpp
.cc
.c
.h
.hpp


配置：

clangd


如果存在：

.py


配置：

pyright


如果没有相关语言：

不要强制安装。


==================================================
十四、compile_commands.json
==================================================


如果检测到：

CMakeLists.txt


检查：

compile_commands.json


如果没有：

提供自动生成能力。


例如：


cmake -B build \
-DCMAKE_EXPORT_COMPILE_COMMANDS=ON


注意：

初始化 AgentForge 时不要擅自执行：

可能非常耗时的大型完整构建。


默认策略：

仅配置。


可以：

提示用户执行：

agentforge prepare


由：

agentforge prepare

负责生成编译数据库。


==================================================
十五、ROS2适配
==================================================


如果检测到：

package.xml

colcon

ament


判断：

ROS2 Workspace / Package


推荐：


colcon build \
--cmake-args \
-DCMAKE_EXPORT_COMPILE_COMMANDS=ON


但：

默认 agentforge init

不要直接完整构建大型 ROS2 workspace。


提供：


agentforge prepare


执行相关准备工作。


==================================================
十六、命令设计
==================================================


至少实现：


agentforge init


初始化当前工程。


agentforge verify


检查：

- opencode
- Main Agent
- workers
- LSP
- build tools
- AGENTS.md


agentforge prepare


准备：

- compile_commands.json
- LSP需要的工程索引信息


agentforge doctor


详细环境诊断。


建议支持：


agentforge init --dry-run


只展示即将进行的修改。


==================================================
十七、幂等性
==================================================


所有操作必须：

idempotent。


重复运行：

agentforge init


不能：

- 重复追加 AGENTS.md
- 重复创建 Agent
- 覆盖用户配置
- 重复安装依赖
- 删除用户文件


==================================================
十八、配置合并原则
==================================================


如果用户已有：

opencode.json

不要直接覆盖。


必须：

读取现有 JSON

然后：

最小增量合并 AgentForge 配置。


如果存在冲突：

创建备份：

例如：

opencode.json.agentforge.bak


并明确提示。


==================================================
十九、禁止行为
==================================================


禁止：

- 删除工程文件
- 重写用户现有 AGENTS.md
- 覆盖用户 opencode 配置
- 修改用户源码
- 自动 git commit
- 自动 git push
- 保存 API Key
- 默认执行大型完整构建
- 默认修改系统级 SSH 配置
- 把 Main Agent 写死为 GPT
- 让 Worker 替代 Main Agent 做最终架构决策


==================================================
二十、README要求
==================================================


README 必须重点解释：


AgentForge 不是：

IDE。


AgentForge 也不是：

一个新的 AI coding agent。


AgentForge 是：

“opencode 多 Agent 开发工作流初始化器”。


核心理念：


Expensive / capable model:

Think


Cheap worker model:

Execute


即：


Main Agent
    |
    | Plan
    ↓
Worker
    |
    | Execute
    ↓
Code
    |
    | Feedback
    ↓
Main Agent


README 要给出：

Windows Local

Windows + Remote SSH Linux

Linux Local

三种完整使用示例。


==================================================
二十一、实现优先级
==================================================


第一阶段优先保证：

P0：

1. Windows本地可运行
2. Linux本地可运行
3. Windows Remote SSH Linux可运行
4. AGENTS.md安全注入
5. deepseek-worker-free配置
6. deepseek-worker配置
7. Main Agent继承当前模型
8. clangd
9. pyright
10. agentforge verify


P1：

- ROS2
- compile_commands
- doctor
- prepare


P2：

后续扩展：

- MCP
- Git Review Worker
- Test Worker
- ROS2 Profile
- PX4 Profile
- RK3588 Profile


==================================================
二十二、最终目标
==================================================


用户进入任何已有工程：


cd project


执行：


agentforge init


之后直接启动：

opencode


Main Agent：

自动使用当前对话选择的模型。


Main Agent 根据任务自动调用：


deepseek-worker-free


或者：

deepseek-worker


形成：


User

↓

Main Agent
(Current Conversation Model)

↓

Plan / Reason / Dispatch

↓

deepseek-worker-free
DeepSeek V4 Flash Free

或者

deepseek-worker
DeepSeek V4 API

↓

Code / Shell / Build / Test

↓

Main Agent Review

↓

User


==================================================
二十三、开发执行要求
==================================================


现在请直接实现完整仓库。

执行顺序：


1. 首先确认当前 opencode 最新版本实际支持的：
   - Agent配置格式
   - 子Agent定义方式
   - 模型/provider配置方式
   - LSP配置格式

不要凭空创造 opencode 配置字段。


2. 根据真实接口设计 AgentForge。


3. 创建完整目录结构。


4. 实现 Windows 和 Linux 脚本。


5. 实现 AGENTS.md 幂等注入。


6. 实现 opencode 配置增量合并。


7. 实现两个 DeepSeek Worker。


8. 实现 verify / doctor。


9. 编写 README。


10. 在本地创建最小测试工程验证：
    - AGENTS.md不存在
    - AGENTS.md已存在
    - 重复init
    - 无DeepSeek API Key
    - 有DeepSeek API Key
    - C++
    - Python


11. 最后输出：

- 最终目录树
- 使用方式
- 配置文件说明
- 已验证测试
- 尚未解决的问题


原则：

优先做出可运行的最小完整版本。

不要只写设计文档。

直接创建代码、脚本、配置和测试。