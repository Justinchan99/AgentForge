# AgentForge Linux usage guide

**English** | [简体中文](usage.zh-CN.md)

AgentForge is installed once for each Linux user. Run `agentforge init` separately in every project that should use the workflow.

## 1. Install on the Linux machine

Clone the deployment branch and install:

```sh
git clone --branch deploy --single-branch https://github.com/Justinchan99/AgentForge.git
cd AgentForge
chmod +x install.sh
./install.sh
```

If the current shell cannot find `agentforge`, run:

```sh
export PATH="$HOME/.local/bin:$PATH"
```

Add the export to `~/.bashrc` or `~/.zshrc` to make it persistent. Before installation, the source-checkout launcher is `./agentforge`; after installation, use `agentforge` from `PATH`.

Confirm the installation:

```sh
agentforge --version
agentforge doctor
```

## 2. Initialize each project

```sh
cd /path/to/project
agentforge init --dry-run
agentforge init --yes
```

The dry run previews changes without writing or installing anything. Use `agentforge init --skip-install` when host dependencies are managed separately.

Initialization manages the AgentForge block in `AGENTS.md`, portable policies in `.agentforge/`, real OpenCode workers in `.opencode/agents/`, project-local OpenCode/LSP configuration, and VS Code recommendations.

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

Confirm the worker configuration:

```sh
opencode agent list
```

The output should include `deepseek-worker-free (subagent)`. The current conversation model is the Main Agent, so no separate `main-agent` entry is expected.

Subagents do not appear in the Tab list of primary agents. The Main Agent can dispatch bounded work automatically, or you can invoke the free worker directly:

```text
@deepseek-worker-free search for the configuration loader and report its call path
```

The default worker may edit project files, asks before running Shell commands, cannot create more agents, and cannot access files outside the project. Architecture decisions and final acceptance remain in the main conversation.

## 4. Enable the optional DeepSeek worker

The free worker does not require a user-provided DeepSeek key. A portable `.agentforge/deepseek-worker.md` template is always generated, but the real `.opencode/agents/deepseek-worker.md` worker is created or enabled only after authentication.

Use OpenCode's preferred interactive flow:

```text
/connect
```

Select DeepSeek, complete authentication, then run:

```sh
agentforge init
agentforge verify
```

Alternatively, provide the key through the current shell environment before initialization:

```sh
export DEEPSEEK_API_KEY="..."
agentforge init
```

Never write API keys into project files or commit them to Git.

## 5. Prepare CMake or ROS 2 indexing

```sh
agentforge prepare
```

`init` never starts a large build. `prepare` explicitly generates CMake or ROS 2 compilation-database inputs. An existing root `compile_commands.json` is preserved.

## 6. Verify and smoke test

```sh
agentforge verify
agentforge doctor
```

`READY` verifies required tools, Agent policies, configured workers, project configuration, model catalog entry, and relevant LSP. It does not mean a worker has run a real task or that the project has built and passed its tests.

Run a small worker smoke task in OpenCode:

```text
@deepseek-worker-free list the top-level project structure without changing files
```

The optional `deepseek-worker` may remain unavailable without making verification fail.

## 7. Update AgentForge

Update and reinstall the user-level runtime:

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

AgentForge updates only its managed `AGENTS.md` block, preserves user JSON values, and creates a one-time `*.agentforge.bak` when a JSON conflict needs a safety backup.

## Remote SSH

When source code is on a remote Linux host, run AgentForge, OpenCode, language servers, builds, and tests on that host through the VS Code Remote SSH terminal. Do not initialize a Windows folder that merely displays remote files.

## Common issues

- Worker missing from Tab: expected for `mode: subagent`; use `@deepseek-worker-free` or automatic Main Agent dispatch.
- Optional worker missing: authenticate DeepSeek, then re-run `agentforge init`.
- clangd or pyright missing: LSP configuration is language-selective; inspect detection with `agentforge doctor`.
- Worker absent after initialization: restart OpenCode with the initialized project as its project context and run `opencode agent list`.
