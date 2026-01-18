#!/usr/bin/env bash
set -euo pipefail

echo "=== Setting up git hooks ==="

HOOKS="$HOME/.config/git/templates/available/hooks"
mkdir -p "$HOOKS" "$HOME/.config/git/hooks"

# Clone git-good-commit
if [ ! -d "$HOOKS/git-good-commit" ]; then
    echo "Installing git-good-commit..."
    git clone --depth=1 https://github.com/tommarshall/git-good-commit.git \
        "$HOOKS/git-good-commit"
    chmod +x "$HOOKS/git-good-commit/hook.sh"
    echo "✓ git-good-commit installed"
else
    echo "✓ git-good-commit already installed"
fi

# Create symlink
ln -sf "$HOOKS/git-good-commit/hook.sh" "$HOME/.config/git/hooks/commit-msg"
echo "✓ commit-msg hook symlinked"

# Create allowed_signers for SSH signing
if [ ! -f "$HOME/.config/git/allowed_signers" ]; then
    touch "$HOME/.config/git/allowed_signers"
    chmod 644 "$HOME/.config/git/allowed_signers"
    echo "✓ allowed_signers file created"
    echo ""
    echo "NOTE: Add your SSH signing key:"
    echo "  echo 'your@email.com \$(cat ~/.ssh/id_ed25519.pub)' >> ~/.config/git/allowed_signers"
else
    echo "✓ allowed_signers already exists"
fi
