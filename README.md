# Watkins 小麥銹病表型統計分析系統

版本識別：`watkins-rust-verified-20261121-b`

這是獨立的 Docker/Flask 專案，資料來自 Watkins 小麥銹病田間觀測 Excel。研究範圍包含 650 筆材料的資料涵蓋分析、描述統計、490 筆完整 Njoro 三日期觀測之 AUDPC、材料查詢及探索性比較。**本系統不是經遺傳試驗驗證的抗病育種名單。**


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
