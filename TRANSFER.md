# Перенос готового комплекта на корпоративный Linux-компьютер

Этот раздел относится к Release **offline-2026-10-01-v1** репозитория **bogdanzolotovski-blip/ai-redteam-offline-kit**. Инструкция предполагает новую Ubuntu 24.04 amd64 и перенос через разрешенный организацией USB/SSD либо внутреннюю файловую шару. На целевом компьютере не требуется доступ к GitHub, Docker Hub, GHCR, Hugging Face или APT-репозиториям.

## 1. Подготовить носитель и папки

Нужны два носителя: загрузочная флешка для Ubuntu ISO и отдельный USB/SSD для файлов комплекта. Для второго подготовьте минимум 64 ГБ свободного места; предпочтительно 128 ГБ. Не используйте FAT32: восстановленный ISO и архив модели больше 4 ГБ. Для переноса Windows → Linux подойдут exFAT или NTFS.

В примере съемный носитель имеет букву `E:`. Проверьте свою букву в Проводнике и замените ее в командах. Создайте:

```text
E:\AI-Redteam\
  kit\        инструкции и скрипты из репозитория
  downloads\  все файлы Release
```

Носитель с файлами не используйте как цель записи ISO: программа записи загрузочного образа может очистить его.

## 2. Скачать все на компьютере с доступом к GitHub

### Через GitHub CLI

В PowerShell на компьютере, где уже доступны GitHub CLI и Git:

```powershell
gh auth login
gh repo clone bogdanzolotovski-blip/ai-redteam-offline-kit E:\AI-Redteam\kit
gh release download offline-2026-10-01-v1 --repo bogdanzolotovski-blip/ai-redteam-offline-kit --dir E:\AI-Redteam\downloads
```

Приватный репозиторий виден только аккаунтам с доступом. Авторизация выполняется на компьютере скачивания. Не копируйте `hosts.yml`, PAT или другие учетные данные GitHub на съемный диск.

### Через браузер

1. Войдите в GitHub аккаунтом с доступом и откройте [репозиторий](https://github.com/bogdanzolotovski-blip/ai-redteam-offline-kit).
2. Нажмите **Code → Download ZIP**, распакуйте содержимое папки репозитория в `E:\AI-Redteam\kit`.
3. Откройте [готовый Release](https://github.com/bogdanzolotovski-blip/ai-redteam-offline-kit/releases/tag/offline-2026-10-01-v1). Если assets скрыты, раскройте их список.
4. Скачайте **все assets** в `E:\AI-Redteam\downloads`, включая `.partNNN`, `.manifest.json`, `MANIFEST.json`, `SHA256SUMS`, исходные Ubuntu SHA256SUMS/signature и отчеты. Архив **Source code (zip)** сам по себе не содержит ISO, контейнеры и веса.
5. Убедитесь, что браузер не оставил `.crdownload`, `.partial` или `.tmp` вместо завершенных частей.

## 3. Проверить и восстановить файлы

На Windows с Python 3:

```powershell
python E:\AI-Redteam\kit\scripts\restore.py E:\AI-Redteam\downloads
```

Либо на Windows без Python, если выполнение PowerShell-скриптов разрешено вашей политикой:

```powershell
powershell -NoProfile -File E:\AI-Redteam\kit\scripts\restore.ps1 -Directory E:\AI-Redteam\downloads
```

Скрипты читают файлы потоком, сверяют размер и SHA256 каждой части и целого архива. Успех обозначается строками `VERIFIED`. При ошибке остановитесь и повторно скачайте указанную часть. Не переименовывайте части, не объединяйте их через текстовый редактор и не меняйте manifests.

После восстановления должны появиться ровно эти девять основных файлов:

```text
ubuntu-24.04.5-live-server-amd64.iso
docker-open-webui.tar.gz
docker-ollama.tar.gz
docker-portainer.tar.gz
docker-ubuntu.tar.gz
ollama-modelstore.tar.gz
ubuntu-packages.tar.gz
open-webui-v0.11.4-source.tar.gz
offline-kit-instructions.tar.gz
```

Части сохраняются. Для хранения одновременно частей и готовых файлов нужен двойной объем места. Основные файлы и служебные manifests необходимо переносить вместе с папкой `kit`.

## 4. Установить ОС и перенести файлы

Запишите **восстановленный** ISO на отдельную загрузочную флешку привычной программой записи образов. Установите Ubuntu Server 24.04 без загрузки обновлений из Интернета. Настройте корпоративный IP/DNS; присоединение к домену не требуется.

После установки подключите носитель с данными. Посмотрите устройство и точку монтирования:

```bash
lsblk -f
```

Если диск уже смонтирован, используйте показанный путь. Если нет, в следующей команде замените `/dev/sdX1` на **раздел вашего носителя**, определенный через `lsblk`:

```bash
sudo mkdir -p /mnt/ai-kit
sudo mount -o ro /dev/sdX1 /mnt/ai-kit
```

Для компьютера Ubuntu Server установка desktop-автомонтирования не нужна. exFAT/NTFS обычно поддерживаются штатным ядром; если носитель не монтируется, перенесите каталог через существующую внутреннюю шару или SSH.

Скопируйте комплект на локальный диск:

```bash
sudo mkdir -p /opt/ai-redteam-offline
sudo cp -a /mnt/ai-kit/AI-Redteam/kit/. /opt/ai-redteam-offline/
sudo cp -a /mnt/ai-kit/AI-Redteam/downloads /opt/ai-redteam-offline/
cd /opt/ai-redteam-offline
sudo python3 scripts/restore.py downloads
```

Если носитель автоматически смонтирован в другом каталоге, замените `/mnt/ai-kit` на фактический путь. Повторная проверка на Linux подтверждает целостность после переноса; `restore.py` вновь сверяет части и готовые файлы. Части заранее не удаляйте.

Альтернативный перенос по SSH с разрешенного внутреннего компьютера:

```powershell
Set-Location E:\
scp -r .\AI-Redteam admin@IP_UBUNTU:/home/admin/
```

На Ubuntu в этом случае копируйте `/home/admin/AI-Redteam/kit/.` и `/home/admin/AI-Redteam/downloads` вместо путей носителя. `admin` и IP — ваши реальные значения. SSH-перенос не требует вступления Ubuntu в домен.

## 5. Установить пакеты и загрузить образы без Интернета

```bash
cd /opt/ai-redteam-offline
sudo tar -xzf downloads/ubuntu-packages.tar.gz
sudo bash scripts/install-packages.sh /opt/ai-redteam-offline/ubuntu-packages
sudo reboot
```

После перезагрузки:

```bash
cd /opt/ai-redteam-offline
nvidia-smi
for image in downloads/docker-*.tar.gz; do gzip -dc "$image" | sudo docker load; done
sudo docker image ls
sudo docker run --rm --pull=never --gpus all -e NVIDIA_DRIVER_CAPABILITIES=utility ubuntu:24.04 nvidia-smi
```

Восстановите том модели:

```bash
sudo docker volume create air_ollama_data
sudo docker run --rm --pull=never \
  -v air_ollama_data:/target \
  -v /opt/ai-redteam-offline/downloads:/bundle:ro \
  ubuntu:24.04 tar -xzf /bundle/ollama-modelstore.tar.gz -C /target
```

Далее выполните [README, шаг 6](README.md#6-portainer-open-webui-ldap): запустите локальный Portainer, разверните Stack, настройте сертификаты, HTTPS и LDAP по [полной инструкции](deployment/README.md). Отключите принудительный pull в Portainer. Команды `docker pull` и `ollama pull` из общего руководства при таком переносе выполнять не нужно.

После запуска Ollama:

```bash
sudo docker cp deployment/Modelfile ollama:/tmp/Modelfile
sudo docker exec ollama ollama create redteam-qwen35-128k -f /tmp/Modelfile
sudo docker exec ollama ollama list
```

## Что вводится уже в корпоративной сети

В комплекте используются примеры: замените `ai.corp.example`, IP, LDAP hostname/base DN/search filter и bind DN. На месте получите корпоративный CA/HTTPS-сертификат, задайте новый `WEBUI_SECRET_KEY`, создайте локального администратора Open WebUI и введите bind-пароль LDAP. Учетные записи сотрудников создаются в существующем AD/LDAP; их пароли не переносятся через GitHub.

Офлайн-проверка пакетов и контрольных сумм не подтверждает работу GPU/LDAP или размещение 128K-контекста: эти проверки выполняются на готовом компьютере. Окно 128K делится между входом, reasoning и ответом; 50–100k свободных токенов нужно проверять на фактическом размере вашего входа.
