#!/bin/zsh
cd -- "$(dirname -- "$0")" || exit 1
export PATH="$HOME/.docker/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
if ! command -v docker >/dev/null 2>&1; then
  echo "找不到 Docker。"
else
  docker compose down
  echo "Watkins 網站的 Docker 容器已停止。"
fi
echo
printf '按 Return 關閉這個視窗。'
read -r answer
