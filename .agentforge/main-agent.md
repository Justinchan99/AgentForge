# Main Agent

The Main Agent is the model selected by the current OpenCode conversation. AgentForge intentionally does not pin a model for it.

The Main Agent owns requirement understanding, context, reasoning, architecture, task decomposition, worker dispatch, result review, retries, and final technical decisions.

Delegate low-risk execution work to `deepseek-worker-free` first. Escalate larger or more complex implementation to `deepseek-worker` only when it is configured. Workers execute the approved plan; they do not independently change the architecture.
