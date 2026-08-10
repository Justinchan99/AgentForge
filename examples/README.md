# Minimal examples

Preview a Python project initialization:

```sh
agentforge init /path/to/python-project --dry-run
```

Initialize without installing missing host tools:

```sh
agentforge init /path/to/project --skip-install
```

Prepare a CMake or ROS 2 compilation database explicitly:

```sh
agentforge prepare /path/to/project
agentforge verify /path/to/project
```

Enable the optional API worker without storing a key in the project:

```sh
export DEEPSEEK_API_KEY="..."   # PowerShell: $env:DEEPSEEK_API_KEY="..."
agentforge init /path/to/project
```

Prefer OpenCode `/connect` for interactive credential storage.
