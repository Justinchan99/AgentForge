# Linux local development

Run `./install.sh` from the AgentForge checkout. The installer supports apt-get and dnf, installs the launcher at `~/.local/bin/agentforge`, and stores the runtime under `$XDG_DATA_HOME/agentforge` or `~/.local/share/agentforge`.

Run `agentforge init` inside each project. clangd is installed/configured only for detected C/C++ projects; pyright only for detected Python projects.

ARM64 is supported when the selected distribution repositories and npm package provide compatible artifacts.
