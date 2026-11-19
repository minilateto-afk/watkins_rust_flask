# Watkins 小麥銹病表型資料分析系統 — 第一階段

**專題定位：** 使用公開的田間試驗表型資料，進行資料清理、描述統計及可互動的 Flask 視覺化。此階段**沒有**進行抗病基因鑑定、抗病育種材料排名、AUDPC、Friedman、Spearman 或因果推論。

## 專題內容

- 原始資料：Watkins 小麥黃銹病／莖銹病／葉銹病 2013 田間觀測。
- 來源：<https://zenodo.org/records/8349020>（DOI: 10.5281/zenodo.8349020）。
- 本版根據 **你上傳的原始 Excel** 建立欄位對照。原始檔沒有改動。
- 650 份材料、29 個有資料的量測欄位；展開成 18,850 筆觀測格紀錄。
- 來源表有三行標題與空白分隔欄，因此不能直接用預設 header=0 讀取。
- 材料編號與試驗觀測分開儲存，保留可追溯的 Excel 欄位號及原始字串。

## 使用 Docker Desktop 執行（推薦）

這是 **Docker 版**。Mac 或 Windows 只要先安裝並啟動 [Docker Desktop](https://www.docker.com/products/docker-desktop/)，**不需要另外安裝 Python、Flask、Pandas**。

### Mac：直接雙擊啟動（最簡單）

1. 解壓縮 ZIP，先開啟 **Docker Desktop**（鯨魚圖示），確認 Docker Engine 已啟動。
2. 在解壓縮後的 `watkins_rust_flask` 資料夾，**雙擊 `docker-start.command`**。
3. 第一次啟動會建立 Docker 映像檔、安裝 Python 套件、重新清理 Excel；成功後會自動開啟 **<http://127.0.0.1:5000>**。
4. 使用完畢可雙擊 `docker-stop.command` 停止。啟動後關閉終端機不會停止網站，也可以直接在 Docker Desktop 的 **Containers** 畫面停止／啟動。

如果 macOS 阻擋 `.command` 執行，可以使用下方「終端機指令」方式。如果提示「Permission denied」，先在資料夾執行 `chmod +x docker-start.command docker-stop.command`。如果提示 Docker 指令不存在，請先在 Docker Desktop 的 Settings 確認 CLI tools 已安裝。

### 終端機指令（Mac / Windows PowerShell / Linux）

先在 Docker Desktop 開啟 Docker Engine，再從終端機進入 `watkins_rust_flask` 資料夾：

```bash
docker compose up --build -d
```

看到 `Started` 或 `Running` 後，在瀏覽器開啟：<http://127.0.0.1:5000>。

常用指令：

```bash
docker compose ps                # 檢查容器狀態
docker compose logs --tail 80    # 查看錯誤訊息
docker compose down              # 停止並移除容器
docker compose up --build -d     # 修改程式或換 Excel 後，重新建立並啟動
```

> **注意：** 每次 `docker compose up --build` 都會從 `data/raw/Watkins.xlsx` 重新計算清理後資料並執行測試。原始 Excel 未被覆寫。`compose.yaml` 只將網站綁定在本機 `127.0.0.1:5000`，不會直接提供給區域網路或網際網路。Docker 映像內含原始 Excel，**請勿把映像上傳至公開 Docker Hub 或其他 Registry**，直到確認資料授權。

### 如果不想用 Docker（備用）

安裝 Python 3.10 以上，在專案資料夾執行：

```bash
python -m pip install -r requirements.txt
python prepare_data.py
python app.py
```

本機開發模式連線位置同樣是 <http://127.0.0.1:5000>；Docker 版則使用 Gunicorn 啟動 Flask，避免公開開啟 Flask debug 模式。

## 網頁頁面

- **統計總覽**：切換銹病、地點、日期及生長期，查看直方圖、平均數、中位數、樣本標準差及資料解析狀況；可匯出選定欄位的 CSV。
- **資料品質**：29 個量測欄的有效值、痕量、區間、缺失比例。
- **材料查詢**：以 Excel 序號、材料編號、名稱或來源國搜尋；檢視原始記錄與不同觀測的散點／折線圖。
- **方法與限制**：明示使用的描述統計與暫時未加入的進階方法。

## 清理規則（重要）

| 原始內容 | 處理方式 | 原因 |
|---|---|---|
| `50MR`、`30S`、`0` | 成株期分成 severity=50/30/0，reaction=MR/S/空 | 單一、明確的量化分數 |
| `TMS`、`TR` | `trace_not_quantified`；severity 保持空白 | 痕量不等於 0 |
| `0-20MSS`、`5-10MS` | `range_or_interval`；severity 保持空白 | 區間並非精確單點分數 |
| `DRY`、`SUSC` | `special_note` | 不是數字百分比 |
| `-`、`---`、`;`、空白 | 分別記為缺失標記／空白 | 未觀測不等於 0 |
| 幼苗期 `0`～`9` | 只進入 `seedling_score` | 原始量尺未確認，**不是病害百分比** |
| 其他（如 `Sr26`） | `unparsed` | 不推測其意義 |

本版描述統計只基於**明確可解析**的觀測值，並清楚呈現排除率。這不是完整資料的無偏估計，也**不能**單靠小數值判斷正式抗病等級。幼苗期的平均值只描述原始數字，沒有「百分比病害」的意義。

日期標籤依原始 2013 欄位與 Excel 日期序列整理。分開保留地點和不同觀測系列，以免把兩個季節或不同田間試驗混成一條曲線。沒有試驗小區／重複區集資訊，本階段不執行品系 ANOVA 或遺傳率推估。

## 檔案說明

```text
watkins_rust_flask/
  app.py                       Flask 路由、描述統計、互動圖表
  prepare_data.py              將原始 Excel 轉為長格式資料，保留審計紀錄
  measurements.py              原始量測欄位 29 項與日期、地點對應
  requirements.txt
  Dockerfile                   Python 環境、資料預處理、Gunicorn 伺服器
  compose.yaml                 一行指令啟動 Docker，僅開放本機埠
  .dockerignore                避免把本機快取和舊 CSV 送入 Docker Build
  docker-start.command         Mac 雙擊啟動
  docker-stop.command          Mac 雙擊停止
  data/raw/Watkins.xlsx        使用者下載的原始檔；不應任意公開再散布
  data/processed/
    observations.csv           每筆材料 × 來源觀測欄（18,850 列）
    materials.csv              650 份材料主檔
    measurement_dictionary.csv 29 個量測欄位對照
    quality_summary.csv        各量測欄位資料品質
    overview.json              記錄數量總結
  templates/                   HTML 網頁
  static/css/                  自訂 RWD 樣式
  static/js/plotly.min.js      本地 Plotly：離線開啟也可顯示互動圖
  tests/                       小型資料規則與完整性檢查
```

## 數學方法與下一階段

目前已做：平均數、樣本標準差、分位數、直方圖、有效值/缺失狀態分布。

**預計但尚未做：** 先確認同材料、同地點、同系列的連續日期及評分規則後再實作 AUDPC（梯形法）。Spearman 與 Friedman 則要再確認研究問題、配對性及推論前提，不能直接套用。

## 學術倫理與授權

- 本專題使用公開科學資料，**不是自行在田間測量**的數據。
- 建議在報告標示：研究資料來源、資料處理原則、數學方法、程式碼與個人實際完成項目。
- 原始資料的具體授權條款要以 Zenodo 原始紀錄的 Rights / License 為準；公開可下載不等於可以再公開重發原始或衍生逐筆資料。
- `.gitignore` 預設排除 raw Excel 與所有 processed CSV，避免在公開 GitHub 上意外再散布。

## 測試

```bash
python -m unittest discover -s tests -v
```
