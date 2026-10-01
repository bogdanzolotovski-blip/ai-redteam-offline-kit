#!/usr/bin/env bash
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo 'Run with sudo'; exit 1; }
source /etc/os-release
[[ "$ID" == ubuntu && "$VERSION_ID" == 24.04 && $(dpkg --print-architecture) == amd64 ]] || { echo 'Ubuntu 24.04 amd64 required'; exit 1; }
bundle=$(realpath "${1:?Pass extracted ubuntu-packages directory}")
cd "$bundle"
sha256sum -c DEBS-SHA256SUMS
driver=$(cat driver-package.txt)
[[ "$driver" =~ ^nvidia-driver-[0-9]+-open$ ]]
sourcefile=$(mktemp --suffix=.list)
trap 'rm -f "$sourcefile"' EXIT
printf 'deb [trusted=yes] file:%s ./\n' "$bundle" > "$sourcefile"
opts=(-o "Dir::Etc::sourcelist=$sourcefile" -o Dir::Etc::sourceparts=- -o Acquire::Languages=none)
apt-get "${opts[@]}" update
apt-get "${opts[@]}" --no-install-recommends -y install "$driver" linux-generic linux-headers-generic build-essential dkms ubuntu-drivers-common docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin nvidia-container-toolkit curl ca-certificates gnupg openssl ldap-utils nginx python3 ufw openssh-server
nvidia-ctk runtime configure --runtime=docker
systemctl enable docker
systemctl restart docker
echo 'Packages installed. Reboot, then check nvidia-smi before starting the stack.'
