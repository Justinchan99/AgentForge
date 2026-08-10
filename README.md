# AgentForge Linux Deployment

**English** | [简体中文](README.zh-CN.md)

This branch is the minimal Linux deployment package for AgentForge. All CLI, project detection, Agent/LSP configuration, migration, dependency installation, CMake/ROS 2 preparation, verification, and embedded templates are contained in the single executable `agentforge` file.

The repository contains only:

```text
.gitattributes
LICENSE
README.md
README.zh-CN.md
agentforge
install.sh
```

`install.sh` is a small bootstrap for machines that do not yet have Python 3.9 or newer. After Python is available, it delegates installation to the self-contained `agentforge` script.

## Architecture

```text
User -> Main Agent (current OpenCode conversation model)
             |
             +--> deepseek-worker-free (default subagent)
             |    opencode/deepseek-v4-flash-free
             |
             `--> deepseek-worker (optional subagent)
                  deepseek/deepseek-v4-pro
```

The Main Agent keeps context, architecture, planning, dispatch, review, and final decisions. Workers execute bounded tasks.

## 1. Install once on each Linux machine

```sh
git clone --branch deploy --single-branch https://github.com/Justinchan99/AgentForge.git
cd AgentForge
chmod +x install.sh agentforge
./install.sh
```

Use `--yes` to allow installation of missing dependencies without prompting:

```sh
./install.sh --yes
```

Use `--skip-tools` when Python 3.9+ and all other dependencies are managed separately:

```sh
./install.sh --skip-tools
```

The installed command is:

```text
~/.local/bin/agentforge
```

No separate AgentForge runtime directory is required. Upgrading removes the legacy `~/.local/share/agentforge` runtime safely after the new single-file command is installed.

If the current Shell cannot find the command:

```sh
export PATH="$HOME/.local/bin:$PATH"
```

Add that export to `~/.bashrc` or `~/.zshrc` to make it persistent.

Confirm installation:

```sh
agentforge --version
agentforge doctor
```

## 2. Initialize every project

AgentForge is installed once per Linux user, but every project must be initialized separately.

```sh
cd /path/to/project
agentforge init --dry-run
agentforge init --yes
agentforge verify
```

- `--dry-run` previews changes without writing files or installing dependencies.
- `--yes` permits installation of missing relevant tools.
- `--skip-install` configures the project without offering dependency installation.
- Re-running `init` is safe and idempotent.

Initialization creates or updates:

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
|       `-- deepseek-worker.md      # only with DeepSeek authentication
`-- .vscode/
    |-- settings.json
    `-- extensions.json
```

## 3. Start OpenCode and use workers

Start OpenCode with the initialized project as its project context:

```sh
cd /path/to/project
opencode
```

or:

```sh
opencode /path/to/project
```

Check the loaded agents:

```sh
opencode agent list
```

The output should include `deepseek-worker-free (subagent)`. The current conversation model is the Main Agent, so no separate `main-agent` entry is expected.

Subagents do not appear in the Tab list of primary agents. The Main Agent can dispatch them automatically, or you can invoke one directly:

```text
@deepseek-worker-free search for the configuration loader and report its call path
```

The default worker may edit project files, asks before running Shell commands, cannot create more agents, and cannot access files outside the project.

## 4. Enable the optional DeepSeek worker

The free worker does not require a user-provided DeepSeek key. The real `.opencode/agents/deepseek-worker.md` worker is created or enabled only after authentication.

Preferred OpenCode flow:

```text
/connect
```

Select DeepSeek, complete authentication, then run:

```sh
agentforge init
agentforge verify
```

Alternatively, provide the key only through the current Shell environment:

```sh
export DEEPSEEK_API_KEY="..."
agentforge init
```

Never write API keys into project files or commit them to Git.

## 5. CMake and ROS 2

`init` detects and configures; it never starts a large build. Generate compilation-database inputs explicitly:

```sh
agentforge prepare
```

An existing root `compile_commands.json` is preserved. ROS 2 environments must be sourced first so `colcon` is available.

## 6. Verify and diagnose

```sh
agentforge verify
agentforge doctor
```

`READY` verifies required tools, Agent policies, configured workers, project configuration, model catalog entry, and relevant LSP. It does not mean a worker has completed a real task or that the project has built and passed its tests.

Run a small Worker smoke task after `READY`:

```text
@deepseek-worker-free list the top-level project structure without changing files
```

The optional `deepseek-worker` may remain unavailable without making verification fail.

## 7. Update

```sh
cd /path/to/AgentForge
git pull
./install.sh
```

Then update every initialized project:

```sh
cd /path/to/project
agentforge init
agentforge verify
```

## Remote SSH

When source code is on a remote Linux host, run AgentForge, OpenCode, language servers, builds, and tests on that host through the VS Code Remote SSH terminal. Do not initialize a Windows directory that merely displays remote files.

## Commands

```text
agentforge init [project] [--dry-run] [--yes] [--skip-install]
agentforge prepare [project] [--dry-run]
agentforge verify [project]
agentforge doctor [project]
```

## Safety

- Existing content outside the managed `AGENTS.md` block is preserved.
- Existing JSON values win; AgentForge only adds missing values.
- JSON conflicts create a one-time `*.agentforge.bak` safety backup.
- Invalid JSON and non-UTF-8 files are reported and left unchanged.
- Legacy AgentForge roles and global LSP configuration are migrated only when they exactly match known generated content.
- `init` does not build, delete, commit, push, or modify project source code.
- Worker templates contain model IDs, never credentials.

## Common issues

- Worker missing from Tab: expected for `mode: subagent`; use `@deepseek-worker-free` or automatic Main Agent dispatch.
- Optional worker missing: authenticate DeepSeek and re-run `agentforge init`.
- clangd or pyright missing: LSP configuration is language-selective; inspect detection with `agentforge doctor`.
- Worker absent after initialization: restart OpenCode with the initialized project as its project context and run `opencode agent list`.

## License

MIT
