# AgentForge

**English** | [简体中文](README.zh-CN.md)

AgentForge is an OpenCode multi-agent workflow initializer. It is not an IDE and it is not a new AI coding agent.

Its core principle is simple:

```text
Capable model: think, plan, decide
Cheap worker:  search, edit, build, test
```

The model selected by the current OpenCode conversation remains the Main Agent. AgentForge does not pin it to GPT, Claude, Gemini, or any other provider. The Main Agent keeps architecture and final decisions, delegates bounded execution work to DeepSeek workers, and reviews their results.

```text
User -> Main Agent (current conversation model)
             |
             +--> deepseek-worker-free (default)
             |    opencode/deepseek-v4-flash-free
             |
             +--> deepseek-worker (optional)
                  deepseek/deepseek-v4-pro
             |
             v
        Code / Shell / Test -> Main Agent review
```

## What gets configured

- A managed workflow block in `AGENTS.md`
- A model-independent Main Agent policy
- `deepseek-worker-free` as an OpenCode subagent
- Optional `deepseek-worker` when DeepSeek authentication exists
- clangd only when C/C++ sources are detected
- pyright only when Python sources are detected
- VS Code language and Remote SSH recommendations
- Safe, additive OpenCode JSON merging
- CMake and ROS 2 compilation-database preparation

Agent markdown uses OpenCode's project-local `.opencode/agents/` format. Worker model IDs are taken from the current OpenCode/Models.dev catalog rather than invented configuration fields.

## Install

The CLI requires Python 3.9 or newer. Installers detect existing tools and install only missing components. API keys are never requested, printed, or written by AgentForge.

### Windows local

```powershell
git clone https://github.com/Justinchan99/AgentForge.git
cd AgentForge
.\install.ps1

cd D:\path\to\project
agentforge init
agentforge verify
```

The installer uses winget for system tools and npm for OpenCode/pyright. It installs clangd only when the target project contains C/C++ and pyright only for Python.

When running directly from the AgentForge source checkout before installation, use `./agentforge.cmd <command>` in PowerShell. The extensionless `./agentforge` file is the POSIX launcher for Linux and macOS shells.

### Linux local

```sh
git clone https://github.com/Justinchan99/AgentForge.git
cd AgentForge
chmod +x install.sh
./install.sh

cd /path/to/project
agentforge init
agentforge verify
```

Ubuntu/Debian (`apt-get`) and Fedora-family (`dnf`) package managers are supported. Both x86_64 and ARM64 are detected; actual package availability remains distribution-specific.

### Windows + Remote SSH Linux

Install and run AgentForge in the remote Linux terminal where the source code lives:

```sh
# VS Code Remote SSH terminal on the Linux host
git clone https://github.com/Justinchan99/AgentForge.git
cd AgentForge
./install.sh

cd /remote/path/to/project
agentforge init
agentforge verify
```

OpenCode, workers, clangd/pyright, builds, tests, and the codebase stay on Linux. Windows provides the VS Code UI, Remote SSH, Git UI, and user interaction. Do not use Windows clangd for a remote Linux checkout.

## Usage guide

See the [English usage guide](docs/usage.md) or [中文使用说明](docs/usage.zh-CN.md) for the complete workflow after installation, including project initialization, OpenCode worker invocation, optional DeepSeek authentication, verification, and troubleshooting.

## Commands

```text
agentforge init [project] [--dry-run] [--yes] [--skip-install]
agentforge prepare [project] [--dry-run]
agentforge verify [project]
agentforge doctor [project]
```

- `init` detects the project, offers to install missing relevant dependencies, safely configures agents/LSP, and never builds the project.
- `prepare` configures CMake or runs the requested ROS 2 preparation to produce compilation-database inputs.
- `verify` checks OpenCode, Main Agent policy, workers, relevant LSP, build tools, and the AGENTS block.
- `doctor` prints detailed host, mode, architecture, tools, languages, CMake, and ROS 2 detection.

`init --dry-run` neither writes files nor installs tools.

## Agent behavior

### Main Agent

The Main Agent is not a separate pinned model. The current conversation model reads the injected workflow and owns:

- requirements and conversation context
- reasoning, architecture, and planning
- task decomposition and worker selection
- worker result review, retries, and final decisions

### deepseek-worker-free

Always configured as a visible `mode: subagent` using:

```yaml
model: opencode/deepseek-v4-flash-free
```

Use it for search, small changes, repetitive edits, tests, builds, logs, and simple debugging.

### deepseek-worker

Configured in `.opencode/agents/` only when AgentForge detects `DEEPSEEK_API_KEY` or an existing DeepSeek credential in `opencode auth list`:

```yaml
model: deepseek/deepseek-v4-pro
```

Authenticate securely with OpenCode's `/connect` flow, or set `DEEPSEEK_API_KEY` in the shell before `agentforge init`. If authentication is absent, initialization still succeeds and reports the API worker as optional/unavailable.

Never commit API keys. AgentForge adds ignore rules for local AgentForge secret files and `*.agentforge.bak` configuration backups.

## Generated files

```text
project/
├── AGENTS.md
├── .gitignore
├── .agentforge/
│   ├── .gitignore
│   ├── main-agent.md
│   ├── deepseek-worker-free.md
│   └── deepseek-worker.md
├── .opencode/
│   ├── opencode.json
│   └── agents/
│       ├── deepseek-worker-free.md
│       └── deepseek-worker.md      # only with DeepSeek auth
└── .vscode/
    ├── settings.json
    └── extensions.json
```

`.agentforge/` contains portable policy templates. `.opencode/agents/` is the directory OpenCode actually loads.

## Safety and idempotency

- Existing `AGENTS.md` content is preserved byte-for-byte outside `<!-- AGENTFORGE:BEGIN -->` / `<!-- AGENTFORGE:END -->`.
- Future updates replace only that owned block.
- Existing JSON values always win; AgentForge only adds missing values.
- A conflict creates a one-time `*.agentforge.bak` before merging.
- Invalid JSON and non-UTF-8 files are reported and left unchanged.
- Worker/API templates contain model IDs, never credentials.
- `init` does not build, delete, commit, push, or modify source code.
- Repeated initialization is idempotent.

## CMake and ROS 2

`agentforge init` only detects and configures. It does not start a large build.

For CMake projects:

```sh
agentforge prepare
```

This performs a CMake configure under `.agentforge/cmake-build` with `CMAKE_EXPORT_COMPILE_COMMANDS=ON`. For ROS 2, `prepare` uses managed colcon build/install/log directories and combines package compilation databases under `.agentforge`.

If a project already has a root `compile_commands.json`, AgentForge preserves and uses it.

## Development and tests

```powershell
python -m unittest discover -s tests -v
python scripts\agentforge.py init --dry-run
python scripts\agentforge.py verify
python scripts\build_deploy.py path\to\deploy-output
```

See [usage](docs/usage.md), [architecture](docs/architecture.md), [Windows](docs/windows.md), [Linux](docs/linux.md), and [Remote SSH](docs/remote-ssh.md) for details.

## License

MIT
