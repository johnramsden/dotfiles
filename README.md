# Ansible Dotfiles Playbook

Ansible Playbook to setup my personal dotfiles.

## Clone Repo

```shell
git clone --recursive git@github.com:johnramsden/dotfiles.git
```

## Setup Instructions

* If encrypting secrets, place a vault password in `secrets/vault_id.pass`
* Copy `local/example` directory to `local/<hostname>`
* Modify `local.yml` and `vault.yml`
* Encrypt `vault.yml`
* Replace submodules in `templates` as needed.

## Usage

Run playbook in test mode:

```shell
ansible-playbook --check --diff \
                 --vault-id secrets/vault_id.pass playbook.yml
```

If it looks as expected remove `--check`.

```shell
ansible-playbook --diff \
                 --vault-id secrets/vault_id.pass playbook.yml
```
