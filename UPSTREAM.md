# Источники и лицензии

Архивы и образы upstream не изменяются. Лицензия на один компонент не распространяется автоматически на весь комплект.

- Ubuntu ISO и DEB-пакеты: https://releases.ubuntu.com/24.04/ и официальные Ubuntu noble repositories. Компоненты Ubuntu имеют разные лицензии; исходные copyright/license notices входят в пакеты и ISO.
- Docker CE / Compose / Buildx / containerd: https://download.docker.com/linux/ubuntu/ и https://github.com/docker; исходные copyright notices остаются в пакетах.
- NVIDIA driver: официальный Ubuntu restricted; исходные условия драйвера сохраняются в пакетах. Open kernel modules: https://github.com/NVIDIA/open-gpu-kernel-modules .
- NVIDIA Container Toolkit: https://nvidia.github.io/libnvidia-container/ и https://github.com/NVIDIA/nvidia-container-toolkit .
- Open WebUI: https://github.com/open-webui/open-webui/tree/v0.11.4 . LICENSE находится в поставляемом source archive. Соблюдайте требования upstream по брендингу; интерфейс в комплекте не переименован.
- Ollama: https://github.com/ollama/ollama/tree/v0.35.0 . MIT license; контейнер содержит свои зависимости с отдельными условиями.
- Portainer CE: https://github.com/portainer/portainer . Исходные notices образа сохранены; digest конкретной LTS-сборки указан в Release.
- Qwen3.5 abliterated: https://ollama.com/huihui_ai/qwen3.5-abliterated и https://huggingface.co/huihui-ai . Смотрите license/model card конкретного upstream-варианта; при сборке сохраняются все Ollama manifest layers, включая license layer при наличии.

Точная происхождение каждого архива указано в его `.manifest.json`; исходные signing keys Docker/NVIDIA и списки источников входят в ubuntu-packages/keys.
