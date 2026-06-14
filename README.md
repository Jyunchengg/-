# 菜市場貨單小幫手 ～ 旖旎統整中

Streamlit 菜市場叫貨單管理小工具。

## 功能特色
- 大輸入框一次貼多筆 LINE 貨單
- 自動辨識客戶（內湖鼎、文德店、內湖、南港、新店... + 任意無數字單行客戶名）
- 解析品項 + 數量 + 單位（支援 斤、件、把、盒、包、支、顆、公斤）
- 左側展開各客戶乾淨明細表
- 右側一鍵生成「品項 × 客戶」交叉總叫貨表 + 總數量
- 支援下載 CSV（Excel 友善 utf-8-sig）與 Excel (.xlsx)
- 清除資料、載入範例、移除單一客戶
- 介面簡潔，適合手機使用

## 本機執行

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 專案檔案
- `app.py`：主程式
- `requirements.txt`：依賴
- `README.md`：本說明

## 授權
自由使用，歡迎改進！
