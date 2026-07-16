#!/usr/bin/env bash
# 安装 Python 依赖；优先使用 PyAV 预编译 wheel，避免 pkgconf + ffmpeg 开发库编译。
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-$ROOT/.venv/bin/python}"

if [[ ! -x "$PYTHON" ]]; then
  PYTHON="$(command -v python3 || command -v python)"
fi

echo "Using Python: $PYTHON ($("$PYTHON" --version 2>&1))"

if ! "$PYTHON" -m pip install --only-binary av -r "$ROOT/requirements.txt"; then
  echo
  echo "PyAV wheel unavailable for this Python/platform."
  echo "Options:"
  echo "  1) Use Python 3.10–3.12 on macOS arm64 / Linux x86_64 (wheels available)"
  echo "  2) Install build deps, then retry without --only-binary:"
  echo "       macOS:  brew install pkgconf ffmpeg"
  echo "       Linux:  sudo apt install pkg-config ffmpeg libavformat-dev libavcodec-dev libavdevice-dev libavutil-dev libswscale-dev libswresample-dev libavfilter-dev"
  exit 1
fi
