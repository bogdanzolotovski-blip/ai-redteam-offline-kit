# Комплект для установки AI red teaming без доступа к upstream-репозиториям

Целевая система: Ubuntu Server 24.04 LTS **amd64**, RTX 5070 Ti 16 ГБ, RAM 32 ГБ. Машина подключается к корпоративной сети без вступления в домен; Open WebUI обращается к существующему LDAP/AD. Каталог и учетные записи AD в комплект не входят.

## Что скачано

Готовые большие файлы публикуются в **Releases** после успешного завершения всех задач сборки. В Git находятся только инструкции и скрипты. Если Release пока Draft или workflow завершился ошибкой, комплект еще не готов.

| Артефакт | Назначение |
|---|---|
| Ubuntu Server 24.04.5 ISO | Установка ОС с USB |
| Open WebUI v0.11.4, Docker linux/amd64 | Веб-интерфейс и LDAP |
| Ollama 0.35.0, Docker linux/amd64 | Локальный сервер модели |
| Portainer CE lts, Docker linux/amd64 | Управление Docker; точный digest записан в manifest |
| Ubuntu 24.04, Docker linux/amd64 | Восстановление тома модели и диагностика |
| huihui_ai/qwen3.5-abliterated:9b-q4_K | Веса, манифесты и шаблон Ollama |
| Ubuntu DEB-пакеты и зависимости | Docker Engine, Compose, NVIDIA open driver, Toolkit, ядро/headers, nginx, LDAP tools, SSH, UFW, Python |
| Open WebUI v0.11.4 исходники | Архив upstream с LICENSE |
| Инструкции и скрипты | Восстановление и развертывание |

Версии пакетов, digest образов, SHA256 всех частей и происхождение файлов сохранены в Release. Пакеты и Portainer фиксируются на момент сборки. Драйвер выбирается из официального Ubuntu noble как самый новый доступный `nvidia-driver-NNN-open` с NNN >= 570.

## 1. Скачать Release с разрешенного компьютера

Репозиторий приватный: понадобится доступ к GitHub аккаунту или предоставленный организацией токен чтения. Сам комплект после скачивания работает без GitHub. Не записывайте токены в файлы комплекта.

```powershell
gh auth login
gh release download offline-2026-10-01-v1 --repo bogdanzolotovski-blip/ai-redteam-offline-kit --dir downloads
git clone https://github.com/bogdanzolotovski-blip/ai-redteam-offline-kit.git
python ai-redteam-offline-kit/scripts/restore.py downloads
```

В Linux используется `python3` вместо `python`. Можно скачать все assets через браузер и взять `restore.py` из репозитория. Части `.part000`, `.part001` и далее должны лежать рядом с соответствующим `.manifest.json`.

Скрипт сверяет размер и SHA256 каждой части и объединенного файла. Он не удаляет части. Требуется примерно вдвое больше дискового места, чем суммарный размер скачанных архивов; подготовьте носитель от 64 ГБ, предпочтительно SSD 128 ГБ. FAT32 не подходит для восстановленных файлов >4 ГБ; используйте exFAT или NTFS для переноса, ext4 на Linux.

Дополнительная проверка в Linux:

```bash
cd downloads
sha256sum -c SHA256SUMS
```

`ubuntu-SHA256SUMS` и `.gpg` — оригинальные файлы Ubuntu. При сборке проверяется SHA256 ISO; GPG-подпись поставляется для независимой проверки и не считается проверенной сборкой. Контрольные суммы подтверждают целостность, а не доверие к произвольному источнику.

## 2. Установить Ubuntu

Запишите восстановленный ISO на USB, загрузите компьютер и установите Ubuntu Server. Для первой установки не выбирайте обновления из Интернета. Настройте статический IP либо DHCP reservation, DNS корпоративного LDAP и синхронизацию времени. Не вступайте в домен. Подробности сборки, BIOS, сети и AD — в [руководстве](deployment/README.md).

При включенном Secure Boot установка DKMS-драйвера может потребовать создания и регистрации MOK-ключа через экран при перезагрузке. Фактическую загрузку драйвера проверяйте `nvidia-smi`; контейнерная сборка этого не проверяет.

## 3. Установить системные пакеты без внешних репозиториев

Перенесите восстановленные архивы и репозиторий на машину, например в `/opt/ai-redteam-offline`. Все дальнейшие команды выполняются из этой папки; `downloads` содержит восстановленные файлы.

```bash
cd /opt/ai-redteam-offline
tar -xzf downloads/ubuntu-packages.tar.gz
sudo bash scripts/install-packages.sh /opt/ai-redteam-offline/ubuntu-packages
sudo reboot
```

Установщик использует только локальный каталог пакетов для данной операции APT. Он проверяет SHA256, ставит ядро generic вместе с headers, драйвер и зависимости. После перезагрузки:

```bash
nvidia-smi
sudo docker --version
sudo docker compose version
sudo nvidia-ctk --version
```

До успешного `nvidia-smi` не продолжайте запуск модели. Для нестандартного OEM/HWE-ядра используется поставляемое generic-ядро; проверьте выбранное ядро через `uname -r` и GRUB. Комплект предназначен для новой Ubuntu 24.04 amd64; обновление произвольной старой установки отдельно не проверено.

## 4. Загрузить контейнеры

```bash
cd /opt/ai-redteam-offline
for image in downloads/docker-*.tar.gz; do gzip -dc "$image" | sudo docker load; done
sudo docker image ls
```

`docker load` восстанавливает теги из архивов; скачивать образы через `docker pull` уже не нужно. В Portainer отключайте принудительное получение новых образов при развертывании. Используйте теги из `deployment/compose.yaml`.

Проверка доступа контейнера к GPU с локальным образом:

```bash
sudo docker run --rm --pull=never --gpus all -e NVIDIA_VISIBLE_DEVICES=all -e NVIDIA_DRIVER_CAPABILITIES=utility ubuntu:24.04 nvidia-smi
```

## 5. Восстановить веса модели

```bash
sudo docker volume create air_ollama_data
sudo docker run --rm --pull=never \
  -v air_ollama_data:/target \
  -v /opt/ai-redteam-offline/downloads:/bundle:ro \
  ubuntu:24.04 tar -xzf /bundle/ollama-modelstore.tar.gz -C /target
```

Архив создан из чистого тома единственной модели; ключи контейнера загрузки удалены. Паролей LDAP, токенов и корпоративных данных в нем нет. Проверка сборки сверяет SHA256 всех model blobs и наличие ссылок из манифеста. Инференс на GPU не проверяется.

## 6. Portainer, Open WebUI, LDAP

```bash
sudo docker volume create portainer_data
sudo docker run -d --name portainer --restart=unless-stopped --pull=never \
  -p 127.0.0.1:9443:9443 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v portainer_data:/data portainer/portainer-ce:lts
```

Первую настройку Portainer выполняйте через SSH-туннель `ssh -L 9443:127.0.0.1:9443 admin@IP`, затем откройте `https://localhost:9443`. В Portainer создайте Stack по `deployment/compose.yaml`, задайте собственный `WEBUI_SECRET_KEY`, подготовьте `/opt/ai-redteam/certs/corp-ca.pem` и измените `WEBUI_URL` на корпоративное имя. Дальше выполните шаги nginx/TLS, первого локального администратора, LDAPS и учетных записей в [deployment/README.md](deployment/README.md). Не используйте команды `pull` из общего руководства: образы и модель уже восстановлены из данного комплекта.

После запуска Ollama создайте профиль модели из локальных весов:

```bash
sudo docker cp deployment/Modelfile ollama:/tmp/Modelfile
sudo docker exec ollama ollama create redteam-local -f /tmp/Modelfile
sudo docker exec ollama ollama list
```

Учетные записи сотрудников создаются в существующем AD/LDAP его администратором. Open WebUI создает свою запись при первом LDAP-входе, а локальный администратор назначает доступ. Обычные пользователи не получают доступ к Portainer или Docker socket.

## 7. Проверить реальный компьютер

В комплекте присутствует `deployment/context_probe.py`; он оценивает фактическое размещение длинного входа. Окно 131072 токена общее для входа, reasoning и ответа. Оно не обещает выдачу 100000 токенов и не подтверждено испытанием на данной RTX 5070 Ti. Для требования 50–100k свободных токенов ограничьте размер входа и сначала проверьте память/скорость на одной сессии. Abliterated-модель также не гарантирует отсутствие любых отказов или качество автоматического пентеста.

Проверки, которые остаются на целевой машине: загрузка драйвера и GPU в контейнере, расход VRAM/RAM на 128K, реальная скорость генерации, сертификат и доступность LDAP, вход пользователя, права pending/user/admin, доступ из корпоративной сети. Полностью автономный pentest-агент и набор атакующих инструментов в текущий комплект не входят: это инфраструктура модели и веб-интерфейса.

## Пересборка

В GitHub Actions запустите `Build verified offline kit` вручную. Workflow сначала создает Draft, скачивает артефакты, проверяет offline-установку runtime-пакетов, сверяет SHA256 загрузок с digest на стороне GitHub и только затем публикует Release. Для новой версии измените теги/дату и проверяемый список артефактов в workflow и `scripts/finalize.py`. Старый комплект без необходимости не перезаписывайте.
