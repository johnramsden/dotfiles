#!/usr/bin/env bash
set -euo pipefail

ZSH_DIR="$HOME/.local/share/oh-my-zsh"

if [ -d "$ZSH_DIR" ]; then
    echo "✓ oh-my-zsh already installed"
    exit 0
fi

echo "Installing oh-my-zsh..."
git clone --depth=1 https://github.com/ohmyzsh/ohmyzsh.git "$ZSH_DIR"
echo "✓ oh-my-zsh installed to $ZSH_DIR"
