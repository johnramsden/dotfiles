# Simple Dotfiles

Dotfiles managed with chezmoi + Ansible, following a simple flat structure inspired by [logandonley/dotfiles](https://github.com/logandonley/dotfiles).

## Hosts

- **fenix, wooly, enix**: Arch Linux (with systemd user services, ed25519 SSH signing)
- **can**: Ubuntu/Canonical (no systemd services, RSA SSH signing, Canonical email)

## Features

- Single repository (no submodules)
- SSH commit signing (no GPG)
- Multi-distro support (Arch + Ubuntu)
- Flat directory structure
- Single Ansible playbook (no roles)
- Fast updates with chezmoi

## Quick Start

### Fresh Install

```bash
curl -sfL https://raw.githubusercontent.com/johnramsden/dotfiles/main/bootstrap.sh | bash
```

Or manually:
```bash
# Install chezmoi first (Arch)
sudo pacman -S chezmoi

# Or Ubuntu
sh -c "$(curl -fsLS get.chezmoi.io)"

# Initialize
chezmoi init --apply git@github.com:johnramsden/dotfiles.git
```

## SSH Signing Setup

### On Arch hosts (fenix, wooly, enix)

```bash
# Generate ed25519 key
ssh-keygen -t ed25519 -C "johnramsden@riseup.net"

# Add to allowed_signers
echo "johnramsden@riseup.net $(cat ~/.ssh/id_ed25519.pub)" >> ~/.config/git/allowed_signers

# Add to GitHub/GitLab as signing key
```

### On can (Ubuntu/Canonical)

```bash
# Generate RSA key
ssh-keygen -t rsa -b 4096 -C "john.ramsden@canonical.com"

# Add to allowed_signers
echo "john.ramsden@canonical.com $(cat ~/.ssh/id_rsa.pub)" >> ~/.config/git/allowed_signers

# Add to GitHub/GitLab as signing key
```

## Daily Usage

```bash
# Edit dotfiles
chezmoi edit ~/.zshrc

# See changes
chezmoi diff

# Apply changes
chezmoi apply

# Update from remote
chezmoi update

# Add new dotfile
chezmoi add ~/.tmux.conf
```

## Update Ansible Playbook

The Ansible playbook runs automatically when `dot_bootstrap/setup.yml` changes (via `run_onchange_bootstrap.sh.tmpl`):

```bash
# Edit playbook
chezmoi edit ~/.local/share/chezmoi/dot_bootstrap/setup.yml

# Apply (automatically runs Ansible due to hash change)
chezmoi apply
```

Or run manually:
```bash
cd ~/.local/share/chezmoi
ansible-playbook dot_bootstrap/setup.yml --ask-become-pass
```

## Directory Structure

```
dotfiles/
├── .chezmoi.toml.tmpl              # Configuration (host/distro detection)
├── .chezmoiignore                  # Per-host exclusions
├── run_once_*.sh                   # One-time setup scripts
├── run_onchange_*.sh.tmpl          # Change-triggered scripts
├── dot_bootstrap/setup.yml         # Single flat Ansible playbook
├── dot_gitconfig.tmpl              # Git config template
├── dot_zshrc                       # Zsh configuration
└── dot_config/                     # Application configs
```

## Architecture

- **Chezmoi**: Manages dotfiles, runs bootstrap scripts, handles templating
- **Ansible**: System packages, repos, services (single flat playbook, no roles)
- **Shell scripts**: Install oh-my-zsh, plugins, git hooks

## Comparison to Old Setup

| Aspect | Old (Ansible) | New (chezmoi+Ansible) |
|--------|---------------|------------------------|
| Repos | 1 main + 6 submodules | 1 single repo |
| Structure | Roles, tasks, templates | Flat, simple |
| Ansible | 7 roles | 1 flat playbook |
| Update | `ansible-playbook` (~30s) | `chezmoi apply` (<1s) |
| Files | ~50+ across repos | ~20 total |
| Complexity | High | Low |

## Troubleshooting

### Chezmoi not found after bootstrap on Ubuntu
```bash
export PATH="$HOME/.local/bin:$PATH"
```

### Re-run setup scripts
```bash
cd ~/.local/share/chezmoi
rm ~/.config/chezmoi/chezmoistate.boltdb
chezmoi init --apply
```

### Verify systemd services (Arch hosts only)
```bash
systemctl --user status ssh-agent.service
systemctl --user status update-flatpaks.timer
```

### Enable services
```bash
systemctl --user enable --now ssh-agent.service
systemctl --user enable --now update-flatpaks.timer
```
