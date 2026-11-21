# Watkins 小麥銹病表型統計分析系統

版本識別：`watkins-rust-verified-20261121-b`

這是獨立的 Docker/Flask 專案，資料來自 Watkins 小麥銹病田間觀測 Excel。研究範圍包含 650 筆材料的資料涵蓋分析、描述統計、490 筆完整 Njoro 三日期觀測之 AUDPC、材料查詢及探索性比較。**本系統不是經遺傳試驗驗證的抗病育種名單。**

## GitHub Codespaces 啟動（推薦）

1. 將 `watkins_rust_verified_20261121.zip` 上傳到 Codespaces 工作區最外層 `/workspaces/watkins_rust_flask`（與既有子資料夾並列）。
2. 在 Codespaces Terminal 執行下列指令。**不要使用 `unzip -q ./*.zip`**：有多個 ZIP 時可能選錯舊檔，甚至把其他 ZIP 當成要解壓的檔案名稱。

```bash
cd /workspaces/watkins_rust_flask
unzip -oq watkins_rust_verified_20261121.zip
cd watkins_rust_verified_20261121
pwd
cat RELEASE_ID.txt
bash codespaces-start.sh
```

執行 `pwd` 時路徑最後必須是 `/watkins_rust_verified_20261121`；`cat RELEASE_ID.txt` 必須顯示 `watkins-rust-verified-20261121-b`。如仍顯示舊版資料夾，請先切換路徑再建構。

3. Docker 建構成功後，到 Codespaces 的 **PORTS** 分頁開啟 **5050** 埠，必要時按 Add Port 新增 `5050`。此埠與舊版使用的 5000 不同，避免連到舊網站。

## Mac Docker Desktop 啟動

1. 解壓縮 `watkins_rust_verified_20261121.zip`，得到全新獨立的 `watkins_rust_verified_20261121` 資料夾。
2. 開啟 Docker Desktop。
3. 雙擊新資料夾內的 `docker-start.command`，自動建構並啟動。
4. 瀏覽 `http://127.0.0.1:5050`。停止網站可雙擊 `docker-stop.command`。

如 macOS 限制 `.command` 執行，可以在該資料夾開啟終端機：

```bash
docker compose up -d --build
```

## 檢查與排錯

```bash
# 在新版專案資料夾內執行
python verify_release.py
python prepare_data.py
python -m unittest discover -s tests -v

# 強制重新建構，排除 Docker 的舊快取
docker compose build --no-cache
docker compose up -d

# 查詢網站執行狀態與錯誤
docker compose ps
docker compose logs --tail=100 web
```

在 Docker 建構過程會重新產生衍生資料並執行完整自動測試。若任一測試失敗，建構會停止，避免出現未驗證的分析結果。`verify_release.py` 會檢查版本識別及主要路由測試是否為新版。

## 主要檔案

| 檔案或資料夾 | 用途 |
|---|---|
| `data/raw/Watkins.xlsx` | 原始來源資料，不直接覆寫 |
| `prepare_data.py` | 清理 650 筆材料及來源觀測 |
| `audpc_analysis.py` | AUDPC 數值積分計算 |
| `findings_analysis.py` | 病程描述與探索性分位數比較 |
| `coverage_analysis.py` | 650 筆材料的數值資料涵蓋分析 |
| `search_utils.py` | 依 Excel 序號、accession、名稱與來源查詢 |
| `app.py`、`templates/`、`static/` | Flask 網站與視覺化 |
| `tests/` | 資料、數學及 HTTP 路由回歸測試 |
| `compose.yaml`、`Dockerfile` | Docker 環境與服務設定 |

## 研究限制與資料使用

650 筆材料各有觀測欄位，但部分分數為缺失、痕量或區間註記；程式不會自行補值。601 筆材料至少有一個可解析的數字評分，其中 490 筆具有 Njoro 三日期完整數值，可計算這一組的 AUDPC。不同地點、不同病害與幼苗期評分不合併成單一抗病分數。此資料僅供描述性研究與探索性比較；不能單獨證實遺傳抗性。

來源資料：Zenodo DOI `10.5281/zenodo.8349020`。原始檔案的再散布授權尚需確認，請不要把包含原始 Excel 的 ZIP 或 Docker 映像當成可自由公開散布的資料產品。
