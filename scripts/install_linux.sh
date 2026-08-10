#!/usr/bin/env sh
set -eu

SOURCE_ROOT=""
ASSUME_YES=0
SKIP_TOOLS=0
INIT_PROJECT=""
PROJECT="."

while [ "$#" -gt 0 ]; do
    case "$1" in
        --source) SOURCE_ROOT=$2; shift 2 ;;
        --yes|-y) ASSUME_YES=1; shift ;;
        --skip-tools) SKIP_TOOLS=1; shift ;;
        --project) PROJECT=$2; shift 2 ;;
        --init)
            if [ "$#" -ge 2 ]; then INIT_PROJECT=$2; shift 2; else INIT_PROJECT=.; shift; fi
            ;;
        *) echo "Unknown option: $1" >&2; exit 2 ;;
    esac
done

if [ -z "$SOURCE_ROOT" ]; then
    SOURCE_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
fi
echo "AgentForge Environment Check"
echo "OS:           $(uname -s)"
echo "Architecture: $(uname -m)"
if [ -n "${SSH_CONNECTION:-}" ] || [ -n "${SSH_CLIENT:-}" ]; then
    echo "Mode:         Windows + SSH Remote Linux"
else
    echo "Mode:         Linux Local Development"
fi
if [ "$(id -u)" -eq 0 ]; then echo "Elevated:     yes"; else echo "Elevated:     no"; fi

if ! command -v python3 >/dev/null 2>&1; then
    install_python=0
    if [ "$SKIP_TOOLS" -eq 0 ] && [ "$ASSUME_YES" -eq 1 ]; then
        install_python=1
    elif [ "$SKIP_TOOLS" -eq 0 ]; then
        printf "Python 3.9+ is missing. Install it now? [y/N] "
        read -r answer
        case "$answer" in y|Y|yes|YES) install_python=1 ;; esac
    fi
    if [ "$install_python" -ne 1 ]; then
        echo "Python 3.9 or newer is required." >&2
        exit 1
    elif command -v apt-get >/dev/null 2>&1; then
        privilege=""; if [ "$(id -u)" -ne 0 ]; then privilege="sudo"; fi
        $privilege apt-get update
        $privilege apt-get install -y python3
    elif command -v dnf >/dev/null 2>&1; then
        privilege=""; if [ "$(id -u)" -ne 0 ]; then privilege="sudo"; fi
        $privilege dnf install -y python3
    else
        echo "No supported package manager found; install Python 3.9+ manually." >&2
        exit 1
    fi
fi
python3 -c 'import sys; assert sys.version_info >= (3, 9)' || {
    echo "Python 3.9 or newer is required." >&2
    exit 1
}

missing=""
needs_cpp=0
needs_python=0
if python3 "$SOURCE_ROOT/scripts/detect_environment.py" --project "$PROJECT" --has-language cpp; then needs_cpp=1; fi
if python3 "$SOURCE_ROOT/scripts/detect_environment.py" --project "$PROJECT" --has-language python; then needs_python=1; fi
tools="git node npm cmake ninja opencode"
if [ "$needs_cpp" -eq 1 ]; then tools="$tools clangd"; fi
if [ "$needs_python" -eq 1 ]; then tools="$tools pyright-langserver"; fi
for tool in $tools; do
    if command -v "$tool" >/dev/null 2>&1; then
        echo "  [OK] $tool"
    else
        echo "  [--] $tool"
        missing="$missing $tool"
    fi
done

install_tools=0
if [ "$SKIP_TOOLS" -eq 0 ] && [ -n "$missing" ]; then
    if [ "$ASSUME_YES" -eq 1 ]; then
        install_tools=1
    else
        printf "Install missing tools with the system package manager? [y/N] "
        read -r answer
        case "$answer" in y|Y|yes|YES) install_tools=1 ;; esac
    fi
fi

if [ "$install_tools" -eq 1 ]; then
    if command -v apt-get >/dev/null 2>&1; then
        privilege=""
        if [ "$(id -u)" -ne 0 ]; then
            if command -v sudo >/dev/null 2>&1; then privilege="sudo"; else
                echo "sudo is required to install system packages." >&2
                exit 1
            fi
        fi
        $privilege apt-get update
        packages="git nodejs npm cmake ninja-build"
        if [ "$needs_cpp" -eq 1 ]; then packages="$packages clangd"; fi
        $privilege apt-get install -y $packages
    elif command -v dnf >/dev/null 2>&1; then
        privilege=""
        if [ "$(id -u)" -ne 0 ]; then privilege="sudo"; fi
        packages="git nodejs npm cmake ninja-build"
        if [ "$needs_cpp" -eq 1 ]; then packages="$packages clang-tools-extra"; fi
        $privilege dnf install -y $packages
    else
        echo "No supported package manager found; install git, Node.js, CMake, Ninja, and clangd manually." >&2
    fi

    if command -v npm >/dev/null 2>&1; then
        privilege=""
        if [ "$(id -u)" -ne 0 ] && command -v sudo >/dev/null 2>&1; then privilege="sudo"; fi
        if [ "$needs_python" -eq 1 ]; then command -v pyright-langserver >/dev/null 2>&1 || $privilege npm install --global pyright; fi
        command -v opencode >/dev/null 2>&1 || $privilege npm install --global opencode-ai
    fi
fi

user_dir=${HOME:?HOME must point to the current user profile}
data_root=${XDG_DATA_HOME:-"$user_dir/.local/share"}
install_root="$data_root/agentforge"
bin_root="$user_dir/.local/bin"
mkdir -p "$install_root" "$bin_root"

source_path=$(CDPATH= cd -- "$SOURCE_ROOT" && pwd)
install_path=$(CDPATH= cd -- "$install_root" && pwd)
if [ "$source_path" != "$install_path" ]; then
    for item in install.sh agentforge README.md LICENSE scripts templates docs; do
        if [ -e "$SOURCE_ROOT/$item" ]; then
            cp -R "$SOURCE_ROOT/$item" "$install_root/"
        fi
    done
fi

launcher="$bin_root/agentforge"
printf '%s\n' '#!/usr/bin/env sh' "exec python3 \"$install_root/scripts/agentforge.py\" \"\$@\"" > "$launcher"
chmod +x "$launcher"

echo "AgentForge CLI installed: $launcher"
python3 "$install_root/scripts/configure_lsp.py" --migrate-global ||
    echo "Legacy global OpenCode configuration could not be inspected; it was preserved." >&2
case ":${PATH:-}:" in
    *":$bin_root:"*) ;;
    *) echo "Add $bin_root to PATH, then open a new shell." ;;
esac

if [ -n "$INIT_PROJECT" ]; then
    "$launcher" init "$INIT_PROJECT"
fi
