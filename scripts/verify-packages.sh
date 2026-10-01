#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
cd /bundle
sha256sum -c DEBS-SHA256SUMS > /tmp/hashes.log
echo 'deb [trusted=yes] file:/bundle ./' > /tmp/offline.list
opts=(-o Dir::Etc::sourcelist=/tmp/offline.list -o Dir::Etc::sourceparts=- -o Acquire::Languages=none)
apt-get "${opts[@]}" update
driver=$(cat driver-package.txt)
# Resolve the whole target install with networking disabled. Driver loading and
# DKMS compilation on the actual RTX workstation must be checked after reboot.
apt-get "${opts[@]}" --simulate --no-install-recommends install "$driver" linux-generic linux-headers-generic build-essential dkms ubuntu-drivers-common docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin nvidia-container-toolkit curl ca-certificates gnupg openssl ldap-utils nginx python3 ufw openssh-server
printf '#!/bin/sh\nexit 101\n' > /usr/sbin/policy-rc.d
chmod +x /usr/sbin/policy-rc.d
apt-get "${opts[@]}" --no-install-recommends -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin nvidia-container-toolkit nginx ldap-utils python3 ufw openssh-server
docker --version
docker compose version
nvidia-ctk --version
