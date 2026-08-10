<!-- AGENTFORGE:BEGIN -->
# AgentForge Workflow

## Architecture

This project uses the AgentForge hierarchical multi-agent development workflow.

Main Agent:

- inherits the model used by the current OpenCode conversation
- maintains conversation context and understands user requirements
- owns reasoning, architecture, planning, and task decomposition
- dispatches bounded execution tasks to worker agents
- reviews worker results and makes final technical decisions

Worker Agents:

### deepseek-worker-free

- Model: DeepSeek V4 Flash Free (`opencode/deepseek-v4-flash-free`)
- Default low-cost execution worker
- Use for code search, small changes, repetitive editing, builds, tests, logs, and simple debugging

### deepseek-worker

- Model: DeepSeek V4 Pro (`deepseek/deepseek-v4-pro`)
- Optional; requires user-provided DeepSeek authentication
- Use for multi-file implementation, complex changes, and larger debugging tasks

## Dispatch Policy

1. The Main Agent analyzes the task and keeps architecture and reasoning responsibilities.
2. Delegate execution-heavy work to `deepseek-worker-free` when practical.
3. Escalate to `deepseek-worker` only when the free worker is insufficient and DeepSeek is configured.
4. Workers follow the approved plan and report architecture problems instead of deciding them independently.
5. The Main Agent reviews all worker results before accepting changes.
6. Run relevant build and tests before final handoff.

## Development Tools

- VS Code: IDE, Git, debugging, and Remote SSH
- OpenCode: Main Agent conversation and worker orchestration
- clangd: C/C++ language intelligence
- pyright: Python language intelligence
<!-- AGENTFORGE:END -->
