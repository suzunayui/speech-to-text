#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 が見つかりません。https://www.python.org/downloads/macos/ から Python 3.11 または 3.12 をインストールしてください。" >&2
  exit 1
fi

PYTHON_VERSION="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
case "$PYTHON_VERSION" in
  3.11|3.12|3.13) ;;
  *) echo "Python 3.11〜3.13 を使用してください（検出: $PYTHON_VERSION）。" >&2; exit 1 ;;
esac

VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"
HASH_FILE="$PROJECT_ROOT/.venv/requirements.sha256"

if [[ ! -x "$VENV_PYTHON" ]]; then
  echo "Python 仮想環境を作成しています..."
  python3 -m venv .venv
fi

CURRENT_HASH="$(shasum -a 256 requirements.txt | awk '{print $1}')"
INSTALLED_HASH="$(test -f "$HASH_FILE" && cat "$HASH_FILE" || true)"
if [[ "$CURRENT_HASH" != "$INSTALLED_HASH" ]]; then
  echo "必要なパッケージと FFmpeg をダウンロードしています..."
  "$VENV_PYTHON" -m pip install --upgrade pip
  "$VENV_PYTHON" -m pip install -r requirements.txt
  printf '%s' "$CURRENT_HASH" > "$HASH_FILE"
fi

echo "アプリを起動します..."
exec "$VENV_PYTHON" app.py
