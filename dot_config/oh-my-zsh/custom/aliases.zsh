#!/usr/bin/zsh

## Custom aliases ##
####################

# root commands
alias suno='sudo nano'

alias s='sudo'

alias screenshot="import -window root ~/Pictures/$(date '+%Y%m%d-%H%M%S').png"
alias gitall="git remote | xargs -L1 git push --all"

# Misc
alias efstab='sudo nano /etc/fstab'

# Takes ip/24 as argument
alias sshscan="sudo nmap -p 22 --open -sV"

## systemd ##

alias timersd='systemctl list-timers | less'
alias startvncserv="systemctl --user start vncserver@:1"
alias unitlist="systemctl list-units --type service --state active"
alias scu-enable-now="scu-enable --now"

systemd_commands=(
  start stop reload restart try-restart isolate kill
  reset-failed enable disable reenable preset mask unmask
  link load cancel set-environment unset-environment edit)
for c in $systemd_commands; do alias scu-$c="systemctl --user $c"; done

## packages ##

alias paced="sudo nano /etc/pacman.conf"

function upall() {
  if [[ $(checkupdates) ]]; then
    if ! sudo pacman -Syu; then
      echo "Update failed"
      return 1
    fi
  else
    echo "No system updates"
  fi

  if [[ $(aur repo --upgrades) ]]; then
    echo "Upgrading aur packages"
    aur chroot --update -D /var/lib/aurbuild/x86_64

    aur sync --upgrades --chroot --temp --makepkg-conf="/etc/makepkg.conf" && \
    sudo pacman -Syy && \
    aur sync --upgrades --chroot --temp --makepkg-conf="/etc/makepkg.conf" && \
    sudo pacman -Syu
  else
    echo "No AUR updates"
  fi
}

## Common taks ##

# Find largest files:
# alias paced="

function delsshhost() {
    sed -i.bak -e "${1}d" "${HOME}/.ssh/known_hosts"
}
