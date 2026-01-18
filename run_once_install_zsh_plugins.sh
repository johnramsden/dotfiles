#!/usr/bin/env bash
set -euo pipefail

PLUGINS="$HOME/.config/oh-my-zsh/custom/plugins"
mkdir -p "$PLUGINS"

echo "=== Installing zsh plugins ==="

# zsh-autosuggestions
if [ ! -d "$PLUGINS/zsh-autosuggestions" ]; then
    echo "Installing zsh-autosuggestions..."
    git clone --depth=1 https://github.com/zsh-users/zsh-autosuggestions.git \
        "$PLUGINS/zsh-autosuggestions"
    echo "✓ zsh-autosuggestions installed"
else
    echo "✓ zsh-autosuggestions already installed"
fi

# you-should-use
if [ ! -d "$PLUGINS/you-should-use" ]; then
    echo "Installing you-should-use..."
    git clone --depth=1 https://github.com/MichaelAquilina/zsh-you-should-use.git \
        "$PLUGINS/you-should-use"
    echo "✓ you-should-use installed"
else
    echo "✓ you-should-use already installed"
fi

echo "✓ All plugins installed"
