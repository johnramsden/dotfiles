# Simple Dotfiles

Dotfiles managed with chezmoi + Ansible, following a simple flat structure inspired by [logandonley/dotfiles](https://github.com/logandonley/dotfiles).

## Hosts

- **fenix, wooly, enix**: Arch Linux (with systemd user services, ed25519 SSH signing)
- **can**: Ubuntu (no systemd services, RSA SSH signing)

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
ssh-keygen -t ed25519 -C "$EMAIL"

# Add to allowed_signers
echo ""$EMAIL" $(cat ~/.ssh/id_ed25519.pub)" >> ~/.config/git/allowed_signers

# Add to GitHub/GitLab as signing key
```

### RSA

```bash
# Generate RSA key
ssh-keygen -t rsa -b 4096 -C "$EMAIL"

# Add to allowed_signers
echo ""$EMAIL" $(cat ~/.ssh/id_rsa.pub)" >> ~/.config/git/allowed_signers

# Add to GitHub/GitLab as signing key
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

### Ubuntu Resolute host with authd

On the Ubuntu Resolute host using authd, run chezmoi with traditional sudo and Ansible pipelining enabled:

```bash
ANSIBLE_BECOME_EXE=/usr/bin/sudo.ws \
ANSIBLE_PIPELINING=true \
chezmoi apply
```

Pipelining resolved the authd authentication-screen timeout on this host; `sudo -v` and selecting `sudo.ws` alone did not. Keep both environment variables set for bootstrap runs on this host.

The bootstrap detects the current account's provider before setting its login shell: local accounts use Ansible's `user` module, while authd accounts use `authctl user set-shell` only when their shell is not already `/usr/bin/zsh`. If neither the local files provider nor authd resolves the account, the bootstrap fails rather than creating a duplicate local account. The authd path requires `authctl` to be installed; add `--tags shell` to the manual playbook command below to run only shell configuration.

For a manual playbook run:

```bash
cd ~/.local/share/chezmoi
ANSIBLE_BECOME_EXE=/usr/bin/sudo.ws \
ANSIBLE_PIPELINING=true \
ansible-playbook dot_bootstrap/setup.yml --ask-become-pass
```
