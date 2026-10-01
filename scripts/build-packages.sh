#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
mkdir -p /out/debs /out/keys
apt-get update
apt-get install -y --no-install-recommends ca-certificates curl gnupg dpkg-dev
curl -fsSL --retry 5 https://download.docker.com/linux/ubuntu/gpg -o /out/keys/docker.asc
gpg --dearmor -o /usr/share/keyrings/docker.gpg /out/keys/docker.asc
echo 'deb [arch=amd64 signed-by=/usr/share/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu noble stable' > /etc/apt/sources.list.d/docker.list
curl -fsSL --retry 5 https://nvidia.github.io/libnvidia-container/gpgkey -o /out/keys/nvidia.asc
gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg /out/keys/nvidia.asc
curl -fsSL --retry 5 https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' > /etc/apt/sources.list.d/nvidia-container-toolkit.list
apt-get update
driver=$(apt-cache pkgnames | grep -E '^nvidia-driver-[0-9]+-open$' | sort -V | tail -1)
[[ "$driver" =~ ^nvidia-driver-([0-9]+)-open$ ]] && (( BASH_REMATCH[1] >= 570 ))
printf '%s\n' "$driver" > /out/driver-package.txt
packages=("$driver" linux-generic linux-headers-generic build-essential dkms ubuntu-drivers-common docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin nvidia-container-toolkit curl ca-certificates gnupg openssl ldap-utils nginx python3 ufw openssh-server apt dpkg)
# Empty package status forces resolution of the complete dependency closure,
# including libraries already installed in the build container.
touch /tmp/empty-status
apt-get -o Dir::State::status=/tmp/empty-status -o Dir::Cache::archives=/out/debs --download-only --no-install-recommends -y install "${packages[@]}"
cd /out
dpkg-scanpackages --multiversion debs /dev/null > Packages
gzip -c Packages > Packages.gz
for file in debs/*.deb; do dpkg-deb -f "$file" Package Version Architecture; done > package-versions.txt
cp /etc/apt/sources.list.d/* /out/keys/
sha256sum debs/*.deb > DEBS-SHA256SUMS
