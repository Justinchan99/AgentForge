#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
assume_yes=0
skip_tools=0
for argument in "$@"; do
    case "$argument" in
        --yes|-y) assume_yes=1 ;;
        --skip-tools) skip_tools=1 ;;
    esac
done

python_ok=0
if command -v python3 >/dev/null 2>&1; then
    if python3 -c 'import sys; raise SystemExit(sys.version_info < (3, 9))'; then
        python_ok=1
    fi
fi

if [ "$python_ok" -eq 0 ]; then
    if [ "$skip_tools" -eq 1 ]; then
        echo "Python 3.9 or newer is required; --skip-tools prevents installation." >&2
        exit 1
    fi
    if [ "$assume_yes" -eq 0 ]; then
        if [ ! -t 0 ]; then
            echo "Python 3.9 or newer is required; rerun with --yes to install it." >&2
            exit 1
        fi
        printf 'Install Python 3.9 or newer? [y/N] '
        read -r answer
        case "$answer" in y|Y|yes|YES) ;; *) exit 1 ;; esac
    fi
    privilege=""
    if [ "$(id -u)" -ne 0 ]; then
        command -v sudo >/dev/null 2>&1 || { echo "sudo is required to install Python." >&2; exit 1; }
        privilege="sudo"
    fi
    if command -v apt-get >/dev/null 2>&1; then
        $privilege apt-get update
        $privilege apt-get install -y python3
    elif command -v dnf >/dev/null 2>&1; then
        $privilege dnf install -y python3
    else
        echo "No supported package manager found; install Python 3.9+ manually." >&2
        exit 1
    fi
fi

if ! command -v python3 >/dev/null 2>&1 || ! python3 -c 'import sys; raise SystemExit(sys.version_info < (3, 9))'; then
    echo "The available python3 is older than 3.9; install Python 3.9+ manually." >&2
    exit 1
fi

exec python3 "$SCRIPT_DIR/agentforge" install "$@"
