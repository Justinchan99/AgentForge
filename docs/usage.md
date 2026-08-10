# AgentForge usage guide

**English** | [简体中文](usage.zh-CN.md)

AgentForge has two scopes:

- Install AgentForge once for each operating-system user.
- Run `agentforge init` once in every project that should use the workflow. Re-running it is safe and updates only AgentForge-managed configuration.

Get the complete cross-platform package from `main` (or `develop` for ongoing development). Linux deployment-only users can clone the smaller `deploy` branch:

```sh
git clone --branch deploy --single-branch https://github.com/Justinchan99/AgentForge.git
```

## 1. Install AgentForge

### Windows

From the AgentForge source checkout:

```powershell
.\install.ps1
```

Open a new PowerShell terminal if the installer added `agentforge` to `PATH`.

### Linux

```sh
chmod +x install.sh
./install.sh
```

If the current shell cannot find `agentforge`, add the user-local binary directory to `PATH`:

```sh
export PATH="$HOME/.local/bin:$PATH"
```

Add the same export to the appropriate shell profile, such as `~/.bashrc` or `~/.zshrc`, to make it persistent.

Before installation, the Linux source-checkout launcher is `./agentforge`. After installation, use the `agentforge` command from `PATH`.

Confirm the installation:

```sh
agentforge --version
agentforge doctor
```

## 2. Initialize a project

Change to the root of the project that OpenCode will work on:

```sh
cd /path/to/project
```

Preview changes without writing or installing anything:

```sh
agentforge init --dry-run
```

Initialize the project and allow installation of missing relevant tools:

```sh
agentforge init --yes
```

Use `--skip-install` when dependencies are managed separately:

```sh
agentforge init --skip-install
```

Initialization creates or updates the managed block in `AGENTS.md`, portable policies under `.agentforge/`, real OpenCode workers under `.opencode/agents/`, project-local OpenCode/LSP configuration, and VS Code recommendations.

## 3. Start OpenCode

Start OpenCode with the initialized project as its project context so it can load `AGENTS.md` and `.opencode/`. Either change directory first:

```sh
cd /path/to/project
opencode
```

or pass the project path directly:

```sh
opencode /path/to/project
```

The current OpenCode conversation model is the Main Agent. AgentForge does not create a separate model named `main-agent`, so no such entry appears in the agent switcher.

Confirm that OpenCode loaded the worker:

```sh
opencode agent list
```

The output should include `deepseek-worker-free (subagent)`. `main-agent` is not expected as a separate entry.

`deepseek-worker-free` is configured as a subagent. It does not appear in the Tab list of primary agents. The Main Agent can dispatch work to it automatically when appropriate; direct `@` invocation remains available:

```text
@deepseek-worker-free search for the configuration loader and report its call path
```

Give workers bounded execution tasks. Keep architecture decisions and final acceptance in the main conversation. The default worker may edit project files, asks before running Shell commands, cannot create more agents, and cannot access files outside the project.

## 4. Enable the optional DeepSeek worker

The free worker is available without a user-provided DeepSeek API key. A portable `.agentforge/deepseek-worker.md` policy template is always generated, but the actual OpenCode worker `.opencode/agents/deepseek-worker.md` is created or enabled only after AgentForge detects DeepSeek authentication.

Preferred interactive setup:

```text
/connect
```

Select DeepSeek in OpenCode, complete authentication, and run initialization again:

```sh
agentforge init
agentforge verify
```

Alternatively, provide the key only through the shell environment before initialization:

```sh
export DEEPSEEK_API_KEY="..."
agentforge init
```

PowerShell:

```powershell
$env:DEEPSEEK_API_KEY="..."
agentforge init
```

Never place API keys in project configuration or commit them to Git.

After authentication, the optional worker can be invoked with a bounded task:

```text
@deepseek-worker implement the approved multi-file change and run the relevant tests
```

## 5. Prepare language intelligence

For a CMake or ROS 2 project that needs a compilation database:

```sh
agentforge prepare
```

`init` never starts a large build. `prepare` is the explicit step that generates CMake or ROS 2 indexing inputs. If the project already has a root `compile_commands.json`, AgentForge preserves it.

## 6. Verify and diagnose

Run verification after initialization or an environment change:

```sh
agentforge verify
```

`READY` means the required runtime, Agent policies, configured workers, project configuration, model catalog entry, and relevant LSP are available. It does not mean a worker has completed a real request or that the project has built and passed its tests. An optional `deepseek-worker` may be reported unavailable without making verification fail.

After `READY`, run a small worker smoke task in OpenCode:

```text
@deepseek-worker-free list the top-level project structure without changing files
```

Inspect host and project detection separately:

```sh
agentforge doctor
```

## 7. Update an existing project

First update the AgentForge checkout and reinstall the user-level runtime.

Linux:

```sh
cd /path/to/AgentForge
git pull
./install.sh
```

Windows:

```powershell
cd D:\path\to\AgentForge
git pull
.\install.ps1
```

Then initialize each project again:

```sh
cd /path/to/project
agentforge init
agentforge verify
```

AgentForge updates only its managed `AGENTS.md` block, preserves user JSON values, and creates a one-time `*.agentforge.bak` when a JSON conflict requires a safety backup.

## Remote SSH

When the source code is on a remote Linux host, install and run AgentForge, OpenCode, language servers, builds, and tests on that Linux host. Use the VS Code Remote SSH terminal for every command in this guide. Do not initialize a local Windows folder that merely displays remote files.

## Common issues

### PowerShell commands produce no output

From an uninstalled Windows source checkout, use the Windows launcher:

```powershell
.\agentforge.cmd verify
.\agentforge.cmd doctor
```

The extensionless `./agentforge` file is the POSIX launcher. After installation, use `agentforge verify` normally.

### The worker is missing from the Tab switcher

This is expected for `mode: subagent`. Invoke it with `@deepseek-worker-free`, or let the Main Agent dispatch it. Start or restart OpenCode from the project root after initialization.

### The optional worker is missing

Complete DeepSeek authentication, then re-run `agentforge init`. Until then, `deepseek-worker-free` remains available.

### clangd or pyright was not configured

LSP setup is language-selective. clangd is configured only when C/C++ sources are detected, and pyright only when Python sources are detected. Use `agentforge doctor` to inspect language detection.
