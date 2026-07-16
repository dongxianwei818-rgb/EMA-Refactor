#!/usr/bin/env bash
# 快速安装语音解码所需的 ffmpeg CLI（AAC 备用解码）。
# PyAV (av) 优先使用 pip 预编译 wheel，通常无需 pkgconf / ffmpeg 开发库。
set -euo pipefail

INSTALL_DIR="${FFMPEG_INSTALL_DIR:-${HOME}/.local/bin}"

ffmpeg_ready() {
  if command -v ffmpeg >/dev/null 2>&1 && ffmpeg -version >/dev/null 2>&1; then
    return 0
  fi
  [[ -x "$INSTALL_DIR/ffmpeg" ]]
}

ensure_install_dir() {
  mkdir -p "$INSTALL_DIR"
}

install_ffmpeg_macos() {
  local arch url tmp
  arch="$(uname -m)"
  case "$arch" in
    arm64) url="https://ffmpeg.martin-riedl.de/redirect/latest/macos/arm64/snapshot/ffmpeg.zip" ;;
    x86_64) url="https://ffmpeg.martin-riedl.de/redirect/latest/macos/amd64/snapshot/ffmpeg.zip" ;;
    *)
      echo "Unsupported macOS architecture: $arch" >&2
      exit 1
      ;;
  esac

  tmp="$(mktemp -d)"
  echo "Downloading static ffmpeg for macOS ($arch)..."
  curl -fsSL "$url" -o "$tmp/ffmpeg.zip"
  unzip -q "$tmp/ffmpeg.zip" -d "$tmp"
  install -m 755 "$tmp/ffmpeg" "$INSTALL_DIR/ffmpeg"
  rm -rf "$tmp"
}

install_ffmpeg_linux() {
  if command -v apt-get >/dev/null 2>&1; then
    echo "Installing ffmpeg via apt (minimal packages)..."
    sudo apt-get update -qq
    sudo apt-get install -y --no-install-recommends ffmpeg
    return
  fi
  if command -v dnf >/dev/null 2>&1; then
    echo "Installing ffmpeg via dnf..."
    sudo dnf install -y ffmpeg
    return
  fi
  if command -v pacman >/dev/null 2>&1; then
    echo "Installing ffmpeg via pacman..."
    sudo pacman -Sy --noconfirm ffmpeg
    return
  fi

  local arch url tmp
  arch="$(uname -m)"
  case "$arch" in
    x86_64) url="https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz" ;;
    aarch64 | arm64) url="https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-arm64-static.tar.xz" ;;
    *)
      echo "Unsupported Linux architecture: $arch" >&2
      exit 1
      ;;
  esac

  tmp="$(mktemp -d)"
  echo "Downloading static ffmpeg for Linux ($arch)..."
  curl -fsSL "$url" -o "$tmp/ffmpeg.tar.xz"
  tar -xJf "$tmp/ffmpeg.tar.xz" -C "$tmp"
  install -m 755 "$tmp"/ffmpeg-*-static/ffmpeg "$INSTALL_DIR/ffmpeg"
  rm -rf "$tmp"
}

print_path_hint() {
  case ":$PATH:" in
    *":$INSTALL_DIR:"*) ;;
    *)
      echo
      echo "Add ffmpeg to PATH (append to ~/.zshrc or ~/.bashrc):"
      echo "  export PATH=\"$INSTALL_DIR:\$PATH\""
      ;;
  esac
}

main() {
  if ffmpeg_ready; then
    if command -v ffmpeg >/dev/null 2>&1; then
      echo "ffmpeg already available: $(command -v ffmpeg)"
    else
      echo "ffmpeg already installed: $INSTALL_DIR/ffmpeg"
      print_path_hint
    fi
    exit 0
  fi

  ensure_install_dir

  case "$(uname -s)" in
    Darwin) install_ffmpeg_macos ;;
    Linux) install_ffmpeg_linux ;;
    MINGW* | MSYS* | CYGWIN*)
      echo "Windows: install ffmpeg with scoop or choco, e.g. scoop install ffmpeg" >&2
      exit 1
      ;;
    *)
      echo "Unsupported OS: $(uname -s)" >&2
      exit 1
      ;;
  esac

  if [[ -x "$INSTALL_DIR/ffmpeg" ]]; then
    echo "ffmpeg installed to $INSTALL_DIR/ffmpeg"
    print_path_hint
  else
    echo "ffmpeg installation failed" >&2
    exit 1
  fi
}

main "$@"
