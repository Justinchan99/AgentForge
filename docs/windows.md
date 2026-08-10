# Windows local development

Run `install.ps1` from the AgentForge checkout. It bootstraps Python when necessary, uses winget for missing system tools, npm for OpenCode and pyright, installs the user-local `agentforge.cmd`, and updates the user PATH idempotently.

From a project root, run `agentforge init`, then `agentforge verify`. Open a new terminal after the first install so PATH changes are visible.

When invoking the CLI directly from the AgentForge source checkout, use `./agentforge.cmd verify` or `./agentforge.cmd doctor` in PowerShell. Do not invoke the extensionless `./agentforge` file there; that file is the POSIX shell launcher. After installation, the PATH command remains simply `agentforge`.

AgentForge does not require administrator rights for its own project files. Individual winget packages may request UAC approval.
