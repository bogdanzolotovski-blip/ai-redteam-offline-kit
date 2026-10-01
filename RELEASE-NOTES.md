# Комплект Ubuntu / RTX 5070 Ti

Ubuntu Server 24.04.5 amd64, Open WebUI v0.11.4, Ollama 0.35.0, Portainer CE lts, Ubuntu 24.04 container, Qwen3.5 abliterated 9B Q4_K, NVIDIA open driver и Ubuntu/Docker/Toolkit DEB-пакеты с зависимостями.

Все большие файлы разбиты на части <2 ГиБ. Скачайте assets, запустите `scripts/restore.py downloads`, затем следуйте README репозитория. SHA256 частей и файлов — в manifests; точные версии и источники — в сопутствующих отчетах.

Сборка проверяет целостность ISO и модели, архитектуру контейнеров, разрешение зависимостей без сети, offline-установку Docker/Toolkit/nginx/LDAP tools и совпадение SHA256 загрузок с GitHub. Работа GPU, LDAP и 128K-контекст на целевом компьютере еще не проверены.

Приватный комплект предназначен для переноса через разрешенные организацией каналы. Компоненты распространяются с исходными лицензиями; исходники Open WebUI включают его LICENSE. Подробности — UPSTREAM.md.
