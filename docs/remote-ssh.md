# Windows + Remote SSH Linux

Open the Linux checkout with VS Code Remote SSH. Install and run AgentForge in the remote terminal, not in a local Windows checkout that merely displays remote files.

The remote Linux host owns OpenCode, Agent workers, clangd/pyright, builds, tests, and source paths. Windows owns the VS Code UI, Remote SSH extension, and user interaction.

This separation ensures language servers see the real Linux compiler flags, include paths, generated files, and filesystem semantics.
