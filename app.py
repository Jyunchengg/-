import streamlit as st
import pandas as pd
import re
from io import BytesIO

# ==================== 頁面設定 ====================
st.set_page_config(
    page_title="菜市場貨單小幫手",
    page_icon="🥬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==================== Session State 初始化 ====================
if "orders" not in st.session_state:
    st.session_state.orders = {}  # {顧客: {品項: {"qty": float, "unit": str}, ...}}

# 用來控制輸入框內容（與 widget key 分離，避免直接寫入 widget 的 session_state key 導致 StreamlitAPIException）
if "paste_content" not in st.session_state:
    st.session_state.paste_content = ""


# ==================== 解析函數 ====================
def parse_text(text: str) -> dict:
    """解析多客戶 LINE 貨單文字，回傳 {顧客: {品項: {"qty": , "unit": }, ...}}"""
    if not text or not text.strip():
        return {}

    # 支援單位（kg 會正規化成公斤）
    units = ["斤", "件", "把", "盒", "包", "支", "顆", "公斤", "kg", "KG"]
    unit_pattern = "|".join(re.escape(u) for u in units)

    # 常見客戶關鍵字（可自行擴充）
    known_customers = [
        "內湖鼎", "文德店", "內湖", "南港", "新店",
        "士林", "大安", "信義", "板橋", "中和", "永和",
        "三重", "蘆洲", "汐止", "樹林", "鶯歌"
    ]

    parsed = {}
    current_customer = None

    # 以換行分割，忽略空行
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    for line in lines:
        # ---- 1. 偵測客戶名稱 ----
        detected = None

        # 優先用已知關鍵字
        for cust in known_customers:
            if cust in line:
                detected = cust
                break

        # 如果這一行完全沒有數字 → 視為自訂客戶名稱（非常實用）
        if detected is None and not re.search(r"\d", line):
            if 1 < len(line) <= 20:  # 避免過長亂字
                detected = line

        if detected:
            current_customer = detected
            if current_customer not in parsed:
                parsed[current_customer] = []
            continue

        # ---- 2. 不是客戶 → 嘗試解析品項 ----
        if current_customer is None:
            continue

        # 尋找「數字 + 單位」
        match = re.search(
            r"(\d+(?:\.\d+)?)\s*(" + unit_pattern + r")",
            line,
            re.IGNORECASE
        )
        if not match:
            continue

        qty = float(match.group(1))
        unit_raw = match.group(2)

        # 正規化單位
        unit = "公斤" if unit_raw.lower() in ("kg", "公斤") else unit_raw

        # 取出品項名稱（數字+單位前後的文字）
        item_part = (line[: match.start()] + line[match.end():]).strip()

        # 清理品項：去掉多餘符號，但保留中英文數字
        item = re.sub(r"^[\s:：\-–—,\.。，、]+|[\s:：\-–—,\.。，、]+$", "", item_part)
        item = item.strip()

        if item:
            parsed[current_customer].append({"item": item, "qty": qty, "unit": unit})

    # ---- 3. 同一客戶內相同品項加總 ----
    final = {}
    for cust, entries in parsed.items():
        agg = {}
        for e in entries:
            key = e["item"]
            if key in agg:
                agg[key]["qty"] += e["qty"]
            else:
                agg[key] = {"qty": e["qty"], "unit": e["unit"]}
        final[cust] = agg

    return final


# ==================== 標題與提示 ====================
st.title("菜市場貨單小幫手 ～ 旖旎統整中")
st.caption("🥬 快速把 LINE 貨單變成乾淨表格，一鍵產出總叫貨表，支援手機操作")

with st.expander("📖 使用說明 & 小提示", expanded=False):
    st.markdown("""
    **步驟：**
    1. 從 LINE 複製一個或多個客戶的貨單文字（可直接整段貼上）。
    2. 貼到下方大輸入框。
    3. 點擊「解析並加入」按鈕。
    4. 左側會出現已加入客戶，點擊展開可看該客戶的個別貨單。
    5. 右側點「生成總叫貨表」即可看到品項 × 客戶 的交叉總表。
    6. 直接下載 CSV 或 Excel 檔案給老闆或自己整理用。

    **解析規則：**
    - 客戶名稱自動辨識：常見如「內湖鼎、文德店、內湖、南港、新店」等。
    - 任意「沒有數字的獨立一行」也會被當成新客戶名稱（超彈性）。
    - 品項格式範例：`紅K 8斤`、`高麗菜 6件`、`玉米筍70盒`、`軟鴨血 10顆`、`紅K8斤` 都支援。
    - 支援單位：斤、件、把、盒、包、支、顆、公斤（kg 自動轉公斤）。

    **小提醒：**
    - 同一客戶同一品項會自動加總數量。
    - 總表只顯示數量，單位請以各客戶明細為準。
    - 手機操作也很順手，建議直向使用。
    """)

# ==================== 輸入區 ====================
st.subheader("📝 貼上客人 LINE 貨單文字")

input_text = st.text_area(
    label="",
    value=st.session_state.paste_content,
    placeholder="例如：\n內湖鼎\n紅K 8斤\n高麗菜 6件\n\n文德店\n玉米筍 70盒\n軟鴨血 10顆",
    height=220,
    key="paste_area",   # 使用獨立的 widget key，內容值用 paste_content 控制
    help="可一次貼多筆不同客戶的貨單"
)

# 按鈕區（橫排）
col_btn1, col_btn2, col_btn3 = st.columns([1.2, 1, 1])
with col_btn1:
    parse_btn = st.button("✅ 解析並加入", type="primary", use_container_width=True)
with col_btn2:
    example_btn = st.button("📋 載入範例資料", use_container_width=True)
with col_btn3:
    clear_btn = st.button("🗑️ 清除所有資料", type="secondary", use_container_width=True)

# 載入範例
if example_btn:
    sample = """內湖鼎
紅K 8斤
高麗菜 6件
文德店
玉米筍 70盒
軟鴨血 10顆
內湖
紅K 5斤
高麗菜 2件
南港
玉米筍 20盒
新店
軟鴨血 3顆
紅K 2斤"""
    new_parsed = parse_text(sample)
    for cust, items in new_parsed.items():
        if cust not in st.session_state.orders:
            st.session_state.orders[cust] = {}
        for item, info in items.items():
            if item in st.session_state.orders[cust]:
                st.session_state.orders[cust][item]["qty"] += info["qty"]
            else:
                st.session_state.orders[cust][item] = info.copy()
    st.success("已載入範例資料！")
    st.session_state.paste_content = ""  # 載入範例後也清空輸入區
    st.rerun()

# 解析並加入
if parse_btn:
    if input_text.strip():
        new_parsed = parse_text(input_text)
        if new_parsed:
            added_customers = []
            for cust, items in new_parsed.items():
                if cust not in st.session_state.orders:
                    st.session_state.orders[cust] = {}
                    added_customers.append(cust)
                for item, info in items.items():
                    if item in st.session_state.orders[cust]:
                        st.session_state.orders[cust][item]["qty"] += info["qty"]
                    else:
                        st.session_state.orders[cust][item] = info.copy()
            st.success(f"✅ 已成功解析並加入 {len(new_parsed)} 位客戶的資料！")
            # 清空輸入框（使用獨立的值變數 + rerun 安全清除）
            st.session_state.paste_content = ""
            st.rerun()
        else:
            st.warning("⚠️ 沒找到可解析的內容。請確認格式是否包含「品項 + 數量 + 單位」，並有客戶名稱。")
    else:
        st.warning("請先在輸入框貼上文字再按解析。")

# 清除所有
if clear_btn:
    st.session_state.orders = {}
    st.session_state.paste_content = ""  # 同時清空輸入框
    st.success("已清除所有資料！")
    st.rerun()

st.divider()

# ==================== 主畫面：左客戶列表 + 右總表 ====================
if st.session_state.orders:
    left_col, right_col = st.columns([1, 1.35], gap="medium")

    # ---------- 左側：已加入客戶列表 ----------
    with left_col:
        st.subheader("📋 已加入客戶列表")
        st.caption(f"目前共 {len(st.session_state.orders)} 位客戶（點擊展開查看明細）")

        for customer in sorted(st.session_state.orders.keys()):
            cust_items = st.session_state.orders[customer]
            with st.expander(f"**{customer}**（{len(cust_items)} 項）", expanded=False):
                # 個別客戶表格
                df_rows = []
                for item, info in cust_items.items():
                    df_rows.append({
                        "品項": item,
                        "數量": info["qty"],
                        "單位": info["unit"]
                    })
                df_cust = pd.DataFrame(df_rows)
                st.dataframe(
                    df_cust,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "數量": st.column_config.NumberColumn(format="%.1f"),
                    }
                )

                # 移除客戶按鈕
                if st.button(f"🗑️ 移除「{customer}」", key=f"del_{customer}", use_container_width=True):
                    del st.session_state.orders[customer]
                    st.rerun()

    # ---------- 右側：總叫貨表 ----------
    with right_col:
        st.subheader("📊 總叫貨表")

        gen_btn = st.button(
            "🚀 生成 / 更新總叫貨表",
            type="primary",
            use_container_width=True,
            help="產生品項為行、客戶為列的交叉總表"
        )

        # 無論按不按，資料存在就顯示總表（反應式，體驗更好）
        # 計算總表
        all_customers = sorted(st.session_state.orders.keys())
        all_items = set()
        for items in st.session_state.orders.values():
            all_items.update(items.keys())
        all_items = sorted(list(all_items))

        summary_rows = []
        for item in all_items:
            row = {"品項": item}
            row_total = 0
            for cust in all_customers:
                qty = st.session_state.orders.get(cust, {}).get(item, {}).get("qty", 0)
                row[cust] = qty if qty > 0 else ""
                row_total += qty
            row["總數量"] = row_total
            summary_rows.append(row)

        summary_df = pd.DataFrame(summary_rows)
        # 調整欄位順序
        summary_df = summary_df[["品項"] + all_customers + ["總數量"]]

        st.dataframe(
            summary_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "總數量": st.column_config.NumberColumn(format="%.1f", help="該品項所有客戶加總"),
            }
        )

        st.caption("💡 空白格 = 該客戶沒有訂購此品項")

        # 下載按鈕
        st.markdown("**下載檔案：**")
        dl_col1, dl_col2 = st.columns(2)

        # CSV（utf-8-sig 讓 Excel 開中文不亂碼）
        csv_data = summary_df.to_csv(index=False, encoding="utf-8-sig")
        with dl_col1:
            st.download_button(
                label="📥 下載 CSV",
                data=csv_data,
                file_name="總叫貨表.csv",
                mime="text/csv",
                use_container_width=True
            )

        # Excel (.xlsx)
        excel_buffer = BytesIO()
        with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
            summary_df.to_excel(writer, index=False, sheet_name="叫貨表")
        excel_buffer.seek(0)
        with dl_col2:
            st.download_button(
                label="📥 下載 Excel (.xlsx)",
                data=excel_buffer,
                file_name="總叫貨表.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

else:
    # 無資料時的提示
    st.info("👆 請在上方輸入框貼上貨單文字，然後點擊「解析並加入」開始使用！")
    st.caption("💡 小提示：先點「載入範例資料」可以快速試用功能。")

# ==================== 底部小提示 ====================
st.divider()
st.caption("菜市場貨單小幫手 ～ 旖旎統整中 | 使用 pandas + Streamlit 製作 | 適合手機直向操作")
