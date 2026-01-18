#!/usr/bin/env bash
set -euo pipefail

echo "=============================================="
echo "  Simple Dotfiles Bootstrap (chezmoi)"
echo "=============================================="
echo ""

# Detect distro
if [ -f /etc/arch-release ]; then
    DISTRO="arch"
    echo "Detected: Arch Linux"
elif [ -f /etc/os-release ]; then
    . /etc/os-release
    if [ "$ID" = "ubuntu" ] || [ "$ID" = "debian" ]; then
        DISTRO="ubuntu"
        echo "Detected: Ubuntu/Debian"
    else
        echo "ERROR: Unsupported distribution: $ID"
        exit 1
    fi
else
    echo "ERROR: Cannot detect distribution"
    exit 1
fi

echo ""

# Install base packages
if [ "$DISTRO" = "arch" ]; then
    echo "Installing base packages (Arch)..."
    sudo pacman -Sy --needed --noconfirm git zsh curl openssh

    if ! command -v chezmoi >/dev/null 2>&1; then
        echo "Installing chezmoi..."
        sudo pacman -S --needed --noconfirm chezmoi
    fi

elif [ "$DISTRO" = "ubuntu" ]; then
    echo "Installing base packages (Ubuntu)..."
    sudo apt-get update
    sudo apt-get install -y git zsh curl openssh-client

    if ! command -v chezmoi >/dev/null 2>&1; then
        echo "Installing chezmoi..."
        sh -c "$(curl -fsLS get.chezmoi.io)" -- -b "$HOME/.local/bin"
        export PATH="$HOME/.local/bin:$PATH"
    fi
fi

echo ""
echo "✓ Base packages installed"
echo ""

# Prompt for repo URL
read -p "Enter dotfiles repo URL (e.g., git@github.com:johnramsden/dotfiles.git): " REPO_URL

# Initialize and apply chezmoi
echo ""
echo "Initializing chezmoi from $REPO_URL..."
chezmoi init --apply "$REPO_URL"

echo ""
echo "=============================================="
echo "  Bootstrap Complete!"
echo "=============================================="
echo ""
echo "Post-install steps:"
echo ""
echo "  1. Generate SSH key (if needed):"
echo "     # On Arch hosts (fenix, wooly, enix):"
echo "     ssh-keygen -t ed25519 -C 'johnramsden@riseup.net'"
echo "     echo 'johnramsden@riseup.net \$(cat ~/.ssh/id_ed25519.pub)' >> ~/.config/git/allowed_signers"
echo ""
echo "     # On can (Ubuntu/Canonical):"
echo "     ssh-keygen -t rsa -b 4096 -C 'john.ramsden@canonical.com'"
echo "     echo 'john.ramsden@canonical.com \$(cat ~/.ssh/id_rsa.pub)' >> ~/.config/git/allowed_signers"
echo ""
echo "  2. Add SSH key to GitHub/GitLab as signing key"
echo ""
echo "  3. Logout and login to activate zsh shell"
echo ""
echo "  4. Verify systemd services (fenix/wooly/enix only):"
echo "     systemctl --user status ssh-agent.service"
echo "     systemctl --user status update-flatpaks.timer"
echo ""
