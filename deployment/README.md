# Linux, RTX 5070 Ti, Portainer, Open WebUI и LDAP

Руководство подготовлено 1 октября 2026 года. Это инструкция для новой установки; команды на целевом Linux-компьютере не выполнялись. Все адреса `corp.example` и сеть `10.20.30.0/24` — примеры, которые нужно заменить.

Цель: компьютер с RTX 5070 Ti 16 ГБ VRAM и 32 ГБ ОЗУ, Linux, локальная модель с ослабленными отказами, Open WebUI через Portainer, HTTPS и аутентификация через существующий LDAP/Active Directory. Linux остаётся самостоятельным сервером, без присоединения к домену.

## 1. Что нужно подготовить

Для основной схемы Ollama, Open WebUI и Portainer работают на одном GPU-компьютере. Portainer управляет контейнерами, Open WebUI предоставляет интерфейс, Ollama выполняет модель. LDAP-сервер уже существует в организации.

```text
Пользователи → HTTPS:443 → Nginx на Linux
                              ↓ localhost:3000
                         Open WebUI в Docker
                           ↙           ↘
            Ollama:11434 в Docker      LDAPS:636 → LDAP/AD
                    ↓
               RTX 5070 Ti

Администратор → SSH-туннель → Portainer:9443
```

LDAP bind не требует членства Linux-компьютера в домене. Достаточно DNS, сетевого доступа к LDAP, доверия к его сертификату и учётной записи для поиска пользователей. Не устанавливайте realmd/SSSD и не выполняйте realm join для этой схемы.

Пример параметров:

| Параметр | Пример |
|---|---|
| Имя Linux-компьютера | ai-redteam-01 |
| IP, закреплённый в DHCP | 10.20.30.50 |
| DNS-имя веб-интерфейса | ai.corp.example |
| LDAP-сервер | dc01.corp.example |
| LDAPS | TCP 636 |
| LDAP search base | DC=corp,DC=example |
| Группа допущенных пользователей | CN=AI-RedTeam-Users,OU=Groups,DC=corp,DC=example |
| Сервисная учётная запись | CN=svc-openwebui,OU=Service Accounts,DC=corp,DC=example |

Попросите администратора инфраструктуры предоставить: DNS-запись для веб-интерфейса, LDAPS-адрес, точные DN, корпоративную цепочку CA в PEM и серверный TLS-сертификат с SAN `ai.corp.example` вместе с ключом. Серверный сертификат и CA LDAP выполняют разные задачи.

Для межсетевого экрана нужны входящие 443 от пользователей и 22 от администраторов; исходящие DNS, NTP и 636 к LDAP. На этапе установки необходим HTTPS-доступ к репозиториям Ubuntu, Docker, NVIDIA, GHCR, Docker Hub и источнику модели. Порты 11434, 3000 и 9443 не публикуются в пользовательскую сеть.

## 2. Сборка компьютера и питание

RTX 5070 Ti имеет 16 ГБ VRAM и типичную мощность GPU 300 Вт. NVIDIA указывает рекомендуемую мощность системы 750 Вт. БП 700 Вт ниже этой рекомендации: по одному номиналу нельзя подтвердить его пригодность. Для новой сборки я рекомендую качественный БП 750–850 Вт с подходящим кабелем питания GPU; уточните требования производителя конкретной видеокарты.

32 ГБ ОЗУ подходят для выбранной модели и интерфейса. Это не увеличивает VRAM: перенос частей модели или кеша в RAM может снижать скорость. Практичная остальная конфигурация — совместимые CPU на 6–8 ядер, плата с полноценным слотом для GPU, два модуля ОЗУ по 16 ГБ, NVMe SSD от 1 ТБ и корпус с местом под карту и достаточным обдувом. Конкретную плату и CPU выбирают совместно, с учётом сокета и версии BIOS.

При выключенном питании установите CPU и охлаждение, RAM в рекомендованные платой слоты, SSD, плату в корпус, БП и видеокарту. Подключите кабели по руководствам компонентов. Проверьте полную посадку разъёма питания GPU и свободное пространство у кабеля. После первого запуска проверьте обнаружение RAM/SSD в UEFI. Не разгоняйте систему перед проверкой стабильности длительной нагрузки.

Источник: [NVIDIA RTX 5070 family](https://www.nvidia.com/en-au/geforce/graphics-cards/50-series/rtx-5070-family/).

## 3. Установить Linux и драйвер

Ниже используется Ubuntu Server 24.04 LTS x86_64. При установке создайте локального администратора, например `ops`, включите OpenSSH, задайте имя сервера. Не выбирайте присоединение к Active Directory. Если Linux уже установлен, переустановка для этой схемы не нужна; команды установки пакетов ниже рассчитаны на Ubuntu.

Используйте DHCP reservation для постоянного IP. Настройте разрешение DNS-имён организации через её DNS и проверьте синхронизацию времени.

```bash
sudo apt update
sudo apt upgrade
sudo apt install -y ubuntu-drivers-common curl ca-certificates gnupg openssl ldap-utils nginx python3
sudo ubuntu-drivers list
sudo ubuntu-drivers install
sudo reboot
```

После загрузки:

```bash
nvidia-smi
getent hosts dc01.corp.example
timedatectl status
```

`nvidia-smi` должен показывать RTX 5070 Ti. Если драйвер уже работает, его не нужно переустанавливать. При Secure Boot выполните требуемую установщиком процедуру регистрации ключа, если она появится. Прежде чем устанавливать контейнеры, исправьте ошибки драйвера на хосте.

Источник: [драйвер NVIDIA в Ubuntu](https://ubuntu.com/server/docs/how-to/graphics/install-nvidia-drivers/).

## 4. Установить Docker Engine

Для новой Ubuntu без ранее установленного Docker:

```bash
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

sudo tee /etc/apt/sources.list.d/docker.sources >/dev/null <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: noble
Components: stable
Architectures: amd64
Signed-By: /etc/apt/keyrings/docker.asc
EOF

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo docker run --rm hello-world
```

Здесь `noble` относится к Ubuntu 24.04. Для другого выпуска используйте его codename по официальной инструкции. Если Docker уже установлен и работает в Portainer, повторно устанавливать его не нужно.

Источник: [Docker Engine на Ubuntu](https://docs.docker.com/engine/install/ubuntu/).

## 5. Разрешить контейнерам пользоваться GPU

```bash
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
  | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -fsSL https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
  | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
  | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list >/dev/null

sudo apt update
sudo apt install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
sudo docker run --rm --gpus all ubuntu:24.04 nvidia-smi
```

Последняя команда должна видеть GPU из контейнера. Перезапуск Docker на уже используемом сервере затрагивает его контейнеры, поэтому учитывайте это при выборе момента выполнения.

Источники: [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html), [GPU в Docker Compose](https://docs.docker.com/compose/how-tos/gpu-support/).

## 6. Подготовить сертификаты и каталоги

```bash
sudo install -d -m 0755 /opt/ai-redteam/certs
```

Поместите сюда предоставленные инфраструктурой файлы:

```text
/opt/ai-redteam/certs/corp-ca.pem          CA для проверки LDAPS, PEM
/opt/ai-redteam/certs/webui.fullchain.pem  сертификат HTTPS и промежуточная цепочка
/opt/ai-redteam/certs/webui.key            приватный ключ HTTPS
```

Установите права:

```bash
sudo chmod 644 /opt/ai-redteam/certs/corp-ca.pem
sudo chmod 644 /opt/ai-redteam/certs/webui.fullchain.pem
sudo chmod 600 /opt/ai-redteam/certs/webui.key
```

В контейнер Open WebUI каталог будет смонтирован как `/certs`. LDAP CA нужно указать именно по пути внутри контейнера. Пользовательские компьютеры должны доверять CA, выпустившему HTTPS-сертификат.

## 7. Установить Portainer

Если Portainer уже управляет Docker на этом компьютере, перейдите к следующему шагу. Для новой установки:

```bash
sudo docker volume create portainer_data
sudo docker run -d \
  --name portainer \
  --restart=always \
  -p 127.0.0.1:9443:9443 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v portainer_data:/data \
  portainer/portainer-ce:lts
```

На компьютере администратора откройте SSH-туннель и оставьте терминал открытым:

```bash
ssh -L 9443:127.0.0.1:9443 -L 3000:127.0.0.1:3000 ops@10.20.30.50
```

Откройте `https://localhost:9443`, создайте администратора Portainer и выберите локальное Docker-окружение. У Portainer изначально собственный самоподписанный сертификат. Его учётная запись независима от пользователей Open WebUI.

Источник: [Portainer CE на Linux](https://docs.portainer.io/start/install-ce/server/docker/linux).

## 8. Развернуть stack в Portainer

В Portainer откройте локальное Docker-окружение → Stacks → Add stack. Назовите stack `ai-redteam`. Вставьте содержимое файла `compose.yaml` из этого комплекта.

В compose замените `https://ai.corp.example` своим адресом. Добавьте в разделе Environment variables переменную `WEBUI_SECRET_KEY`, сгенерировав значение:

```bash
openssl rand -hex 32
```

Сохраните ключ в хранилище секретов организации. Доступ к настройкам и environment контейнеров в Portainer получают только администраторы: переменные среды доступны администраторам Docker.

Нажмите Deploy the stack. Это Docker Standalone stack, не Swarm. Используются версии Ollama `0.35.0` и Open WebUI `v0.11.4`, найденные в официальных релизах при подготовке инструкции. При установке позднее проверьте исправления и актуальные стабильные версии, затем зафиксируйте проверенные теги или digest.

Важные свойства compose:

- GPU выделен контейнеру Ollama; Open WebUI не требует отдельного GPU.
- Ollama доступен другим контейнерам stack по `http://ollama:11434`, без опубликованного порта на хосте.
- Open WebUI доступен на хосте только через `127.0.0.1:3000`.
- Модели сохраняются в `air_ollama_data`, пользователи/чаты/настройки — в `air_webui_data`.
- LDAP пока выключен: сначала создаётся локальный администратор Open WebUI.
- Окно Ollama задано 131072 токена, один одновременный запрос и одна модель в памяти.

Проверьте:

```bash
sudo docker ps
sudo docker logs --tail 100 ollama
sudo docker logs --tail 100 open-webui
```

Источники: [подключение Open WebUI к Ollama](https://docs.openwebui.com/getting-started/quick-start/connect-a-provider/starting-with-ollama/), [релиз Open WebUI](https://github.com/open-webui/open-webui/releases/tag/v0.11.4), [релиз Ollama](https://github.com/ollama/ollama/releases/tag/v0.35.0).

## 9. Создать локального администратора Open WebUI

Через уже открытый SSH-туннель перейдите на `http://localhost:3000`. Создайте первый аккаунт с отдельным адресом, например `admin-recovery@corp.example`, который не совпадает с mail LDAP-пользователя. Первый аккаунт становится администратором.

В Admin Panel → Settings → Authentication проверьте:

- New Sign Ups / регистрация выключена после создания администратора.
- Default User Role = `pending`.
- Password authentication включена: её отключение блокирует и LDAP-пароли.
- Локальный административный вход работает и сохранён для восстановления.

Не создавайте первым случайного LDAP-пользователя. Первый пользователь свежей базы становится администратором, независимо от выбранного способа входа.

Источники: [роли Open WebUI](https://docs.openwebui.com/features/authentication-access/rbac/roles/), [параметры аутентификации](https://docs.openwebui.com/reference/env-configuration/).

## 10. Загрузить модель и профиль 128K

Выбрана community-модель Huihui Qwen3.5 9B Abliterated. Автор описывает её как версию с ослабленными отказами; это не гарантия полного отсутствия отказов и не подтверждённый рейтинг качества автопентеста.

```bash
sudo docker exec ollama ollama pull huihui_ai/qwen3.5-abliterated:9b-q4_K
```

Этот вариант занимает около 6,6 ГБ под загрузку модели. Не используйте тег `latest`: у этой серии он указывает на более крупную модель.

Скопируйте файл `Modelfile` из комплекта на Linux, например в `/opt/ai-redteam/Modelfile`, затем:

```bash
sudo docker cp /opt/ai-redteam/Modelfile ollama:/tmp/Modelfile
sudo docker exec ollama ollama create redteam-qwen35-128k -f /tmp/Modelfile
sudo docker exec -it ollama ollama run redteam-qwen35-128k
```

Попросите модель кратко объяснить разницу между прямой и косвенной prompt injection. Проверьте переключатель thinking/reasoning в интерфейсе после подключения. Для совместимого API `think: true` запрашивает рассуждение; поддерживаемые режимы конкретной модели проверяются через `/api/show`.

Источник: [Huihui Qwen3.5 9B](https://huggingface.co/huihui-ai/Huihui-Qwen3.5-9B-abliterated), [теги Ollama](https://ollama.com/huihui_ai/qwen3.5-abliterated/tags).

## 11. Как трактовать требование 50–100K токенов на reasoning

Вход, история, результаты инструментов, reasoning и итоговый ответ используют общее окно. Reasoning не имеет независимого дополнительного окна памяти.

Для `num_ctx=131072`:

| Вход вместе с системным промптом и историей | Теоретический остаток до генерации |
|---:|---:|
| 20000 токенов | 111072 токена |
| 28000 токенов | 103072 токена |
| 64000 токенов | 67072 токена |

Оставляйте дополнительный запас на шаблон сообщений и итоговый ответ. При длинной истории нельзя обещать те же 100K. На каждом ходе агент должен учитывать весь реально переданный вход и при необходимости сокращать историю или результаты инструментов.

Файл Modelfile задаёт `num_predict=110000` как верхнюю границу общей генерации. Это не обязательная длина reasoning и не выделенные 110K только для него. Модель может закончить намного раньше; длительные рассуждения могут зациклиться или потерять качество. Клиент может переопределить этот лимит, поэтому проверьте реальные параметры запроса.

Если модель реально генерирует 100000 токенов, время равно `100000 / скорость`. Например, при измеренной скорости 20–50 токенов/с это около 33–83 минут без учёта обработки входа и действий инструментов. Эти скорости — примеры для расчёта, а не измерение RTX 5070 Ti. Я согласен оставить такой запас окна, но не рекомендую заставлять каждый ход расходовать его полностью.

Qwen3.5 9B использует гибридную архитектуру, имеет нативное окно 262144 токена; авторы советуют сохранять минимум 128K для thinking-задач. Это характеристика исходной модели. Возможности производной abliterated-модели на конкретном backend, квантовании и GPU требуют проверки.

Кеш `q8_0` выбран для сокращения расхода памяти; в Ollama он зависит от поддержки Flash Attention выбранным backend. По одной переменной среды нельзя подтвердить фактическое использование кеша. Проверьте логи. 16 ГБ VRAM не дают гарантии режима 128K; при переносе на CPU измерьте задержку. ОЗУ 32 ГБ не следует считать эквивалентом дополнительных 32 ГБ VRAM.

В Open WebUI откройте параметры модели и задайте `num_ctx=131072` либо уберите его переопределение. Проверьте `num_predict`/Max Tokens: небольшой лимит в интерфейсе отменит большой лимит из Modelfile. Включите thinking. Если обычным пользователям разрешены изменения параметров, они также могут менять окно и лимиты.

Источники: [карточка исходной Qwen3.5 9B](https://huggingface.co/Qwen/Qwen3.5-9B), [память и кеш Ollama](https://docs.ollama.com/faq), [API chat и thinking](https://docs.ollama.com/api/chat).

## 12. Проверить режим длинного контекста

После первого запроса:

```bash
sudo docker exec ollama ollama ps
nvidia-smi
sudo docker logs --tail 200 ollama
```

Проверьте окно 131072, размещение модели (`100% GPU` для полного GPU-размещения), память, выбранный backend и отсутствие OOM. Одна проверка с коротким сообщением не доказывает работу с длинным входом.

Скопируйте `context_probe.py` на Linux и запустите:

```bash
sudo docker cp /opt/ai-redteam/context_probe.py open-webui:/tmp/context_probe.py
sudo docker exec open-webui python /tmp/context_probe.py
```

Тест обращается к Ollama внутри Docker-сети, калибрует синтетический вход около 26K и 64K токенов, запрашивает короткий ответ и печатает реальные счётчики. Во втором терминале наблюдайте `nvidia-smi` и `ollama ps`. Он может работать заметное время.

Этот тест проверяет обработку длинного входа и позволяет вычислить остаток окна. Он НЕ доказывает успешную генерацию 100K токенов reasoning, качество такого рассуждения или скорость автопентеста. Чтобы принять именно это требование, нужен отдельный прогон на представительной разрешённой задаче с анализом полного результата, счётчиков, задержки и памяти.

Если 128K не помещается, сначала подтвердите применение Q8-кеша и одного запроса. Q4-кеш является отдельным экспериментом с возможной потерей качества. Переход на меньшую модель, частичный CPU-offload или GPU с большей VRAM — варианты, которые нужно измерить; уменьшение окна до 8K не выполняет заявленное требование.

## 13. Включить HTTPS

Скопируйте `nginx.conf` из комплекта в `/etc/nginx/sites-available/ai-redteam`, заменив DNS-имя и проверив пути сертификатов.

```bash
sudo ln -s /etc/nginx/sites-available/ai-redteam /etc/nginx/sites-enabled/ai-redteam
sudo nginx -t
sudo systemctl enable --now nginx
sudo systemctl reload nginx
```

Если используете UFW, сначала разрешите SSH с административной сети, затем HTTPS с пользовательской. Пример для новой машины:

```bash
sudo ufw allow from 10.20.30.0/24 to any port 22 proto tcp
sudo ufw allow from 10.20.30.0/24 to any port 443 proto tcp
sudo ufw enable
```

Замените подсети своими до выполнения. Docker имеет собственные правила публикации портов, поэтому защита здесь опирается также на отсутствие published port у Ollama и loopback-публикацию Open WebUI/Portainer.

Откройте `https://ai.corp.example`. Браузер должен доверять сертификату, а ответы должны поступать потоково. Nginx-конфигурация предусматривает WebSocket и длительное ожидание ответа.

Источник: [HTTPS и reverse proxy для Open WebUI](https://docs.openwebui.com/reference/https/).

## 14. Подготовить LDAP/Active Directory

Основной вариант ниже — существующий Microsoft AD с LDAPS. Действия выполняет администратор каталога через Active Directory Users and Computers или принятую в организации систему управления.

1. Создать группу безопасности `AI-RedTeam-Users`, запомнить её полный DN.
2. Создать сервисного пользователя `svc-openwebui` для bind и поиска. Нужны права чтения нужных пользователей/атрибутов, без административных полномочий. Настроить пароль и его ротацию по политике организации.
3. Для каждого участника создать или использовать личную учётную запись AD, заполнить уникальный атрибут `mail`, добавить её напрямую в группу.
4. Проверить состояние учётной записи и доступность LDAPS на контроллере домена.

Open WebUI не создаёт пользователей в AD. Он проверяет пароль в каталоге и создаёт собственную запись пользователя после первого успешного LDAP-входа.

Если каталог — OpenLDAP, обычно username-атрибут `uid`, email-атрибут `mail`, user objectClass `inetOrgPerson`. Фильтр группы зависит от схемы: `memberOf` работает, только если каталог действительно предоставляет этот атрибут. Не переносите AD-фильтр на OpenLDAP без адаптации.

## 15. Проверить LDAPS до настройки UI

С Linux-хоста:

```bash
openssl s_client \
  -connect dc01.corp.example:636 \
  -servername dc01.corp.example \
  -verify_hostname dc01.corp.example \
  -CAfile /opt/ai-redteam/certs/corp-ca.pem \
  -verify_return_error </dev/null
```

Ожидается успешная проверка цепочки и имени сертификата. Далее проверьте поиск; пароль вводится интерактивно через `-W`:

```bash
LDAPTLS_CACERT=/opt/ai-redteam/certs/corp-ca.pem ldapsearch \
  -x -H ldaps://dc01.corp.example:636 \
  -D 'CN=svc-openwebui,OU=Service Accounts,DC=corp,DC=example' -W \
  -b 'DC=corp,DC=example' \
  '(&(sAMAccountName=ivan.petrov)(memberOf=CN=AI-RedTeam-Users,OU=Groups,DC=corp,DC=example))' \
  dn cn mail sAMAccountName
```

Должна вернуться одна нужная запись с mail. Убедитесь также, что DNS и TCP 636 доступны из контейнера Open WebUI. Успешная проверка на хосте не гарантирует контейнерную сетевую доступность.

Проверка TLS из контейнера без передачи учётных данных:

```bash
sudo docker exec open-webui python -c 'import socket,ssl; ctx=ssl.create_default_context(cafile="/certs/corp-ca.pem"); conn=ctx.wrap_socket(socket.create_connection(("dc01.corp.example",636),timeout=10),server_hostname="dc01.corp.example"); print("LDAPS TLS OK:",conn.version()); conn.close()'
```

Результат подтверждает DNS/TCP/TLS из контейнера. Bind и разрешение входа пользователей проверяются отдельно.

## 16. Настроить LDAP в Open WebUI

Зайдите локальным администратором → Admin Panel → Settings → Authentication → LDAP. Заполните:

| Поле | Пример для AD |
|---|---|
| Enable LDAP | включено |
| Server label | Corporate LDAP |
| Host | dc01.corp.example, без `ldaps://` |
| Port | 636 |
| Use TLS | включено |
| Validate certificate | включено |
| CA certificate path | /certs/corp-ca.pem |
| App DN | CN=svc-openwebui,OU=Service Accounts,DC=corp,DC=example |
| App password | пароль сервисной учётной записи |
| Search base | DC=corp,DC=example |
| Username attribute | sAMAccountName |
| Mail attribute | mail |

В Search filter добавьте условия:

```ldap
(&(objectCategory=person)(objectClass=user)(memberOf=CN=AI-RedTeam-Users,OU=Groups,DC=corp,DC=example)(!(userAccountControl:1.2.840.113556.1.4.803:=2)))
```

Это пример для непосредственного членства в группе. Если используются вложенные группы AD, фильтр нужно адаптировать и проверить отдельными учётными записями.

Не включайте в поле шаблоны `%s` или `%(user)s`: Open WebUI сам добавляет username-фильтр. При `sAMAccountName` пользователь вводит `ivan.petrov`, без `DOMAIN\` и без суффикса UPN. Для входа полным UPN можно выбрать `userPrincipalName` и протестировать его отдельно.

Сохраните настройки. В текущей реализации Use TLS означает LDAPS с TLS сразу при подключении. StartTLS на порту 389 этим переключателем не включается.

Настройки LDAP сохраняются в базе. После первого запуска смена environment-переменной в Portainer может не изменить сохранённое значение. Для этой инструкции меняйте LDAP через Admin Panel и оставьте persistent config включённым.

Источники: [LDAP Open WebUI](https://docs.openwebui.com/features/authentication-access/auth/ldap/), [параметры среды](https://docs.openwebui.com/reference/env-configuration/), [реализация аутентификации v0.11.4](https://raw.githubusercontent.com/open-webui/open-webui/v0.11.4/backend/open_webui/routers/auths.py).

## 17. Создать записи пользователей в Open WebUI и выдать доступ

Откройте приватное окно браузера, выберите LDAP-вход и войдите личной учётной записью из разрешённой группы. После проверки каталога запись в Open WebUI создастся автоматически.

Локальный администратор открывает Admin Panel → Users и переводит нового пользователя из `pending` в `user`. Роль `admin` выдаётся только администраторам платформы. Проверьте доступ пользователя к модели и к его собственным чатам.

Общую регистрацию оставьте выключенной. `ENABLE_SIGNUP` не заменяет LDAP-фильтр: правила допуска LDAP-пользователей определяет поиск каталога. Не создавайте заранее дубли с тем же mail и отдельным локальным паролем без конкретной необходимости.

При отзыве доступа удалите пользователя из группы или заблокируйте его в AD, а в Open WebUI отзовите активные сессии/ключи и деактивируйте его доступ. Не считайте исключение из LDAP-группы мгновенным завершением уже выданной сессии. Проверьте это тестом в своей версии.

## 18. Приёмка установки

Установка принимается, когда подтверждены все пункты:

- Хост и контейнер Ollama видят RTX 5070 Ti.
- Модель отвечает, её режим thinking поддерживается и включён.
- Реальный запрос использует контекст 131072; проверены длинный вход и остаток окна.
- Для требований к 50–100K reasoning отдельно зафиксированы качество и время представительной генерации. Тест короткого ответа этого не доказывает.
- После перезагрузки модель, пользователи, чаты и настройки сохраняются.
- HTTPS доверен пользовательским компьютерам.
- LDAP-пользователь из разрешённой группы входит; пользователь вне группы и с неверным паролем не входит.
- Новые пользователи получают pending, а не admin.
- Обычный пользователь не имеет административных прав Open WebUI/Portainer.
- На сетевом интерфейсе хоста не опубликованы Ollama:11434, Open WebUI:3000 и Portainer:9443.
- Linux не зарегистрирован как доменный компьютер.

При длительной генерации наблюдайте температуру GPU, память, ошибки и время ответа. Не заявляйте стабильность БП или качество автопентеста только по успешному запуску интерфейса.

## 19. Резервные копии и обслуживание

Храните резервные копии `air_webui_data`, `portainer_data`, WEBUI_SECRET_KEY, конфигураций и сертификатов. Том Ollama можно восстанавливать повторным скачиванием модели, но для воспроизводимости сохраните её идентификатор/digest и Modelfile.

Для согласованной файловой копии SQLite остановите Open WebUI перед копированием его тома, затем запустите снова. Проверьте восстановление в отдельной тестовой установке. Не удаляйте volumes при пересоздании stack.

Перед обновлением версии сохраните базу; обновление может менять её схему, поэтому откат одного image не всегда откатывает данные.

Пользователи Open WebUI и пользователи Portainer — разные системы. LDAP для входа в Open WebUI настраивается внутри Open WebUI, а не в Portainer.

Если Portainer физически находится на другом сервере, используйте его подключение к Docker GPU-хоста и разворачивайте этот stack именно в GPU-окружении. Для варианта, где Open WebUI и Ollama находятся на разных физических хостах, потребуется отдельный защищённый канал между ними; текущий compose рассчитан на один хост.
