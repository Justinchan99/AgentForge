# Architecture

AgentForge configures a hierarchical workflow around OpenCode. The active conversation model is the Main Agent and remains provider-independent. It owns reasoning, architecture, task decomposition, dispatch, review, and final decisions.

`deepseek-worker-free` is the default execution subagent. `deepseek-worker` is an optional higher-capability execution subagent enabled only when DeepSeek authentication is detected. Both workers are prevented from spawning further agents or accessing files outside the project by default.

AgentForge uses `AGENTS.md` for the Main Agent dispatch policy and `.opencode/agents/*.md` for real OpenCode subagents. LSP configuration is project-local and language-selective.
