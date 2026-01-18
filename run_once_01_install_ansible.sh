#!/usr/bin/env bash
set -euo pipefail

if command -v ansible-playbook &> /dev/null; then
    echo "✓ Ansible already installed"
    exit 0
fi

echo "Installing Ansible..."

if [ -f /etc/arch-release ]; then
    sudo pacman -Sy --needed --noconfirm ansible
elif [ -f /etc/os-release ]; then
    . /etc/os-release
    if [ "$ID" = "ubuntu" ] || [ "$ID" = "debian" ]; then
        sudo apt-get update
        sudo apt-get install -y ansible
    fi
fi

echo "✓ Ansible installed"
