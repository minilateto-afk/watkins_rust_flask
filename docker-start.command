#!/bin/zsh
# Double-click on macOS after installing Docker Desktop.
cd -- "$(dirname -- "$0")" || exit 1
export PATH="$HOME/.docker/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

pause_exit() {
  echo
  echo "按 Return 關閉這個視窗。"
  read -r answer
  exit "$1"
}

if ! command -v docker >/dev/null 2>&1; then
  echo "找不到 Docker 指令。請先安裝並開啟 Docker Desktop。"
  pause_exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "Docker Desktop 尚未啟動，嘗試開啟 Docker Desktop..."
  open -a Docker
  for i in {1..45}; do
    if docker info >/dev/null 2>&1; then break; fi
    sleep 2
  done
fi

if ! docker info >/dev/null 2>&1; then
  echo "Docker 尚未準備好。請先確認鯨魚圖示顯示 Docker Engine 正在運作，再重新開啟此檔案。"
  pause_exit 1
fi

echo "目前專案：$(pwd)"
echo "版本識別：$(cat RELEASE_ID.txt)"
echo "正在建立並啟動 Watkins Flask 網站（第一次使用會下載 Python 基底映像與套件）。"
if ! docker compose up --build --detach; then
  echo "啟動失敗，請檢查上方訊息或執行 docker compose logs。"
  pause_exit 1
fi

ready=0
for i in {1..30}; do
  if curl --silent --fail "http://127.0.0.1:5050/health" >/dev/null; then
    ready=1
    break
  fi
  sleep 2
done

if [[ "$ready" == "1" ]]; then
  echo "網站已啟動：http://127.0.0.1:5050"
  open "http://127.0.0.1:5050"
  echo "可以關閉這個終端機視窗；網站會持續由 Docker Desktop 運行。"
else
  echo "容器已提交啟動，但網站尚未通過健康檢查。請執行 docker compose logs 查看原因。"
fi
pause_exit 0
