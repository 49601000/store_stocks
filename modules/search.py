"""
search.py  v4
在庫検索 & フラグ更新タブ

追加:
  - モデル名クリック → st.dialog モーダルで全カラム詳細表示
"""

import streamlit as st
import pandas as pd
from datetime import date
from modules import data as D
from modules.settings import get_allowed_brands, get_fav_brands

# ─────────────────────────────────────────────
#  定数
# ─────────────────────────────────────────────
FLAG_OPTIONS = ["", "〇", "△", "▲", "×"]
FLAG_LABELS_DISPLAY = {
    "":  "在庫有",
    "〇": "〇売上済",
    "△": "△スタッフ",
    "▲": "▲返品",
    "×": "×除外",
}

_ROW_CLASS = {
    "〇": "row-sold",
    "△": "row-staff",
    "▲": "row-return",
    "×": "row-discard",
    "":  "row-stock",
}

# ─────────────────────────────────────────────
#  CSS
# ─────────────────────────────────────────────
_CSS = """
<style>
.row-sold    { background:#f5ede0; border-radius:6px; padding:4px 6px; margin-bottom:2px; }
.row-staff   { background:#e0eefc; border-radius:6px; padding:4px 6px; margin-bottom:2px; }
.row-return  { background:#ede0f5; border-radius:6px; padding:4px 6px; margin-bottom:2px; }
.row-discard { background:#e8e8e8; border-radius:6px; padding:4px 6px; margin-bottom:2px; }
.row-stock   { background:transparent; padding:4px 6px; margin-bottom:2px; }
.col-label   { font-size:0.75rem; color:#666; margin-bottom:1px; font-weight:600; }

/* テーブル行フォント縮小 */
div[data-testid="stHorizontalBlock"] p,
div[data-testid="stHorizontalBlock"] div[data-testid="stText"] {
    font-size: 0.78rem !important;
    line-height: 1.3 !important;
}
div[data-testid="stHorizontalBlock"] div[data-baseweb="select"] {
    font-size: 0.78rem !important;
}
div[data-testid="stHorizontalBlock"] input {
    font-size: 0.78rem !important;
}

/* 詳細ボタンをリンク風に */
.detail-btn > button {
    background: none !important;
    border: none !important;
    padding: 0 !important;
    color: #1a73e8 !important;
    font-size: 0.78rem !important;
    text-decoration: underline !important;
    cursor: pointer !important;
    text-align: left !important;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 100%;
}
.detail-btn > button:hover {
    color: #0d47a1 !important;
    background: none !important;
}
</style>
"""

# ─────────────────────────────────────────────
#  詳細モーダル（st.dialog）
# ─────────────────────────────────────────────
@st.dialog("📋 商品詳細", width="large")
def _show_detail(row: pd.Series):
    flag  = str(row.get("売上フラグ", "")).strip()
    brand = str(row.get("ブランド", ""))
    model = str(row.get("モデル", ""))

    # タイトル部
    flag_color = {"〇":"#c8a96e","△":"#6ea8c8","▲":"#a06ec8","×":"#999"}
    fc = flag_color.get(flag, "#4CAF50")
    raw_id = row.get("ID", "")
    try:
        display_id = str(int(float(raw_id)))
    except Exception:
        display_id = str(raw_id)

    st.markdown(
        f"### {brand}　{model}",
        help=f"ID: {display_id}"
    )
    if flag:
        st.markdown(
            f'<span style="background:{fc};color:#fff;padding:3px 12px;'
            f'border-radius:4px;font-weight:bold;">'
            f'{FLAG_LABELS_DISPLAY.get(flag, flag)}</span>',
            unsafe_allow_html=True
        )
    st.divider()

    # ── 全カラムをグループ別に表示 ──────────────
    def clean(val):
        s = str(val)
        return "―" if s in ["", "nan", "None", "NaN"] else s

    def price(val):
        try:
            return f"¥{int(float(val)):,}"
        except Exception:
            return clean(val)

    # 基本情報
    st.markdown("#### 基本情報")
    r1c1, r1c2, r1c3, r1c4 = st.columns(4)
    r1c1.metric("ID",     display_id)
    r1c2.metric("ブランド", clean(row.get("ブランド","")))
    r1c3.metric("モデル",  clean(row.get("モデル","")))
    r1c4.metric("カラー",  clean(row.get("カラー","")))

    # 価格情報
    st.markdown("#### 価格情報")
    p1, p2, p3 = st.columns(3)
    p1.metric("上代（税込）", price(row.get("上代（税込）","")))
    p2.metric("下代",        price(row.get("下代","")))
    # 税抜き計算（上代が取れる場合）
    try:
        tax_excl = int(int(float(row.get("上代（税込）",0))) / 1.1)
        p3.metric("上代（税抜）", f"¥{tax_excl:,}")
    except Exception:
        p3.metric("上代（税抜）", "―")

    # 在庫・売上情報
    st.markdown("#### 在庫・売上情報")
    s1, s2, s3, s4, s5 = st.columns(5)
    s1.metric("店舗",      clean(row.get("店舗","")))
    s2.metric("売上フラグ", FLAG_LABELS_DISPLAY.get(flag, "在庫有"))
    s3.metric("売上年",    clean(row.get("売上年","")))
    s4.metric("売上月",    clean(row.get("売上月","")))
    s5.metric("入荷年月日", clean(row.get("入荷年月日","")))

    # 移動情報
    st.markdown("#### 移動情報")
    m1, m2, m3 = st.columns(3)
    m1.metric("移動元", clean(row.get("移動元","")))
    m2.metric("移動先", clean(row.get("移動先","")))
    m3.metric("移動日", clean(row.get("移動日","")))

    # 備考・その他（残り全カラムを表示）
    known_cols = {
        "ID","ブランド","モデル","カラー","上代（税込）","下代",
        "店舗","売上フラグ","売上年","売上月","入荷年月日",
        "移動元","移動先","移動日","備考"
    }
    extra_cols = [c for c in row.index if c not in known_cols]

    memo = clean(row.get("備考",""))
    if memo != "―":
        st.markdown("#### メモ・備考")
        st.info(memo)

    if extra_cols:
        st.markdown("#### その他項目")
        ex_vals = {c: clean(row.get(c,"")) for c in extra_cols if clean(row.get(c,"")) != "―"}
        if ex_vals:
            ecols = st.columns(min(len(ex_vals), 4))
            for i, (k, v) in enumerate(ex_vals.items()):
                ecols[i % 4].metric(k, v)

    st.divider()
    if st.button("✕ 閉じる", use_container_width=True):
        st.rerun()


# ─────────────────────────────────────────────
#  メイン描画
# ─────────────────────────────────────────────
def render(df: pd.DataFrame):
    st.markdown(_CSS, unsafe_allow_html=True)
    st.subheader("在庫検索 & フラグ更新")

    # ── フィルタ行 ───────────────────────────
    fa, fb, fc, fd, fe = st.columns([1, 2, 2, 1.5, 1.2])

    with fa:
        st.markdown('<p class="col-label">🔎 ID</p>', unsafe_allow_html=True)
        search_id = st.text_input("ID", placeholder="例: 1234",
                                  label_visibility="collapsed", key="s_id")
    with fb:
        st.markdown('<p class="col-label">📋 モデル名</p>', unsafe_allow_html=True)
        search_model = st.text_input("モデル", placeholder="モデル名",
                                     label_visibility="collapsed", key="s_model")
    with fc:
        st.markdown('<p class="col-label">🎨 カラー</p>', unsafe_allow_html=True)
        search_color = st.text_input("カラー", placeholder="カラー",
                                     label_visibility="collapsed", key="s_color")
    with fd:
        st.markdown('<p class="col-label">🏪 店舗</p>', unsafe_allow_html=True)
        store_filter = st.radio(
            "店舗", ["マトイ", "ニコメ", "両方"],
            index=2, label_visibility="collapsed", key="s_store",
        )
    with fe:
        st.markdown('<p class="col-label">　</p>', unsafe_allow_html=True)
        show_all = st.toggle("売済も表示", value=False, key="s_showall")

    # ── フィルタリング ──────────────────────
    result = df.copy()

    if not show_all:
        result = result[result["売上フラグ"].fillna("").astype(str).str.strip() == ""]
    if store_filter != "両方" and "店舗" in result.columns:
        result = result[result["店舗"].astype(str).str.strip() == store_filter]

    allowed_brands = get_allowed_brands()
    if allowed_brands and "ブランド" in result.columns:
        result = result[result["ブランド"].astype(str).str.strip().isin(allowed_brands)]

    if search_id.strip():
        result = result[result["ID"].astype(str).str.contains(search_id.strip(), case=False, na=False)]
    if search_model.strip():
        result = result[result["モデル"].astype(str).str.contains(search_model.strip(), case=False, na=False)]
    if search_color.strip():
        result = result[result["カラー"].astype(str).str.contains(search_color.strip(), case=False, na=False)]

    fav_brands = get_fav_brands()
    if fav_brands and "ブランド" in result.columns:
        result = result.copy()
        result["_is_fav"] = result["ブランド"].astype(str).str.strip().isin(fav_brands)
        result = result.sort_values("_is_fav", ascending=False).drop(columns=["_is_fav"])

    # ── 件数 ────────────────────────────────
    total_stock = len(df[df["売上フラグ"].fillna("").astype(str).str.strip() == ""])
    if show_all:
        st.caption(f"表示: {len(result)} 件（全体在庫: {total_stock} 件）")
    else:
        st.caption(f"在庫あり: {len(result)} 件 ／ 総データ: {len(df)} 件　※売済等は非表示")

    if len(result) > 200:
        st.warning("200件以上のため最初の200件を表示します。")
        result = result.head(200)

    if result.empty:
        st.info("該当する商品がありません。")
        return

    st.divider()

    # ── ヘッダー行 ───────────────────────────
    COL_W   = [0.35, 0.6, 1.3, 2.0, 1.0, 0.65, 0.85, 0.95, 1.4, 0.9, 0.65, 1.8]
    HEADERS = ["⭐","ID","ブランド","モデル","カラー","店舗","下代","上代(税込)","フラグ","年","月","メモ"]
    h = st.columns(COL_W)
    for col, label in zip(h, HEADERS):
        col.markdown(f"**{label}**")
    st.divider()

    # ── データ行 ────────────────────────────
    today  = date.today()
    years  = list(range(today.year, today.year - 6, -1))
    months = list(range(1, 13))

    def fmt_price(val):
        try:
            return f"¥{int(float(val)):,}"
        except Exception:
            return "―"

    for row_idx, row in result.iterrows():
        flag   = str(row.get("売上フラグ", "")).strip()
        brand  = str(row.get("ブランド", "")).strip()
        model  = str(row.get("モデル", ""))
        is_fav = brand in fav_brands
        row_class = _ROW_CLASS.get(flag, "row-stock")

        st.markdown(f'<div class="{row_class}">', unsafe_allow_html=True)
        c = st.columns(COL_W)

        # ⭐
        c[0].write("⭐" if is_fav else "")

        # ID（整数表示）
        raw_id = row.get("ID", "")
        try:
            display_id = str(int(float(raw_id)))
        except Exception:
            display_id = str(raw_id)
        c[1].write(display_id)

        # ブランド
        c[2].write(brand)

        # モデル名：リンク風ボタン → クリックで詳細モーダル
        with c[3]:
            st.markdown('<div class="detail-btn">', unsafe_allow_html=True)
            if st.button(
                model if model not in ["", "nan"] else "（未設定）",
                key=f"detail_{row_idx}",
                help="クリックで詳細表示",
            ):
                _show_detail(row)
            st.markdown("</div>", unsafe_allow_html=True)

        c[4].write(str(row.get("カラー", "")))
        c[5].write(str(row.get("店舗", "")))
        c[6].write(fmt_price(row.get("下代", "")))
        c[7].write(fmt_price(row.get("上代（税込）", "")))

        # フラグ プルダウン
        cur_flag_idx = FLAG_OPTIONS.index(flag) if flag in FLAG_OPTIONS else 0
        sel_flag = c[8].selectbox(
            "フラグ",
            options=FLAG_OPTIONS,
            index=cur_flag_idx,
            format_func=lambda x: FLAG_LABELS_DISPLAY.get(x, x),
            key=f"flag_sel_{row_idx}",
            label_visibility="collapsed",
        )
        if sel_flag != flag:
            _apply_flag(df, row_idx, sel_flag, row)

        # 年・月
        cur_year  = row.get("売上年",  "")
        cur_month = row.get("売上月", "")
        try:
            yi = years.index(int(float(cur_year))) if str(cur_year) not in ["", "nan"] else 0
        except Exception:
            yi = 0
        try:
            mi = months.index(int(float(cur_month))) if str(cur_month) not in ["", "nan"] else today.month - 1
        except Exception:
            mi = today.month - 1

        sel_year  = c[9].selectbox("年",  years,  index=yi, key=f"yr_{row_idx}",  label_visibility="collapsed")
        sel_month = c[10].selectbox("月", months, index=mi, key=f"mo_{row_idx}", label_visibility="collapsed")

        if sel_flag == "〇" and (sel_year != cur_year or sel_month != cur_month):
            if c[9].button("↑保存", key=f"ymupd_{row_idx}", help="年月を更新"):
                updated = D.update_flag(df.copy(), row_idx, "〇", year=sel_year, month=sel_month)
                D.save(updated)
                st.success(f"ID {display_id} 年月を {sel_year}/{sel_month} に更新しました")
                st.rerun()

        # メモ欄
        cur_memo = str(row.get("備考", "")) if str(row.get("備考", "")) not in ["nan", "None"] else ""
        new_memo = c[11].text_input(
            "メモ", value=cur_memo, key=f"memo_{row_idx}",
            label_visibility="collapsed", placeholder="メモ...",
        )
        if new_memo != cur_memo:
            updated = df.copy()
            updated.at[row_idx, "備考"] = new_memo
            D.save(updated)
            st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  フラグ適用
# ─────────────────────────────────────────────
def _apply_flag(df: pd.DataFrame, idx: int, flag: str, row):
    updated = D.update_flag(df.copy(), idx, flag)
    D.save(updated)
    label = D.FLAG_LABELS.get(flag, flag)
    st.success(f"ID {row.get('ID','')} → {label} に更新しました")
    st.rerun()
