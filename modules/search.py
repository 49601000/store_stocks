"""
search.py  v3
在庫検索 & フラグ更新タブ

変更点:
  ① フラグ変更をプルダウン方式に（スペース削減）
  ② メモ欄追加（スプレッドシートの「備考」列を読み込み・更新）
  ③ 検索入力ラベルを入力欄の上に配置
  ④ 店舗ラジオボタンを「マトイ / ニコメ / 両方」縦2段レイアウト
  ⑥ フラグ色で行全体を網掛け（〇ベージュ / △薄青 / ▲薄紫 / ×グレー）
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
    "":  "― 在庫あり",
    "〇": "〇 売上済み",
    "△": "△ スタッフ用",
    "▲": "▲ 返品",
    "×": "× 破棄",
}

# フラグ → 行背景色（薄い網掛け）
FLAG_BG = {
    "〇": "#f5ede0",   # ベージュ
    "△": "#e0eefc",   # 薄青
    "▲": "#ede0f5",   # 薄紫
    "×": "#e8e8e8",   # グレー
    "":  "transparent",
}

# ─────────────────────────────────────────────
#  CSS
# ─────────────────────────────────────────────
_CSS = """
<style>
/* 行網掛け用コンテナ */
.row-sold    { background:#f5ede0; border-radius:6px; padding:4px 6px; margin-bottom:2px; }
.row-staff   { background:#e0eefc; border-radius:6px; padding:4px 6px; margin-bottom:2px; }
.row-return  { background:#ede0f5; border-radius:6px; padding:4px 6px; margin-bottom:2px; }
.row-discard { background:#e8e8e8; border-radius:6px; padding:4px 6px; margin-bottom:2px; }
.row-stock   { background:transparent; padding:4px 6px; margin-bottom:2px; }

/* ヘッダーラベル */
.col-label { font-size:0.75rem; color:#666; margin-bottom:1px; font-weight:600; }
</style>
"""

_ROW_CLASS = {
    "〇": "row-sold",
    "△": "row-staff",
    "▲": "row-return",
    "×": "row-discard",
    "":  "row-stock",
}

# ─────────────────────────────────────────────
#  メイン描画
# ─────────────────────────────────────────────
def render(df: pd.DataFrame):
    st.markdown(_CSS, unsafe_allow_html=True)
    st.subheader("在庫検索 & フラグ更新")

    # ── ③ フィルタ行：ラベルを入力欄の上に配置 ──
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
        # ④ ラジオボタン配置：マトイ・ニコメ を上段、両方を下段
        st.markdown('<p class="col-label">🏪 店舗</p>', unsafe_allow_html=True)
        store_filter = st.radio(
            "店舗",
            ["マトイ", "ニコメ", "両方"],
            index=2,
            label_visibility="collapsed",
            key="s_store",
        )

    with fe:
        st.markdown('<p class="col-label">　</p>', unsafe_allow_html=True)
        show_all = st.toggle("売済も表示", value=False, key="s_showall")

    # ── データフィルタリング ──────────────────
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

    # お気に入りを先頭に
    fav_brands = get_fav_brands()
    if fav_brands and "ブランド" in result.columns:
        result = result.copy()
        result["_is_fav"] = result["ブランド"].astype(str).str.strip().isin(fav_brands)
        result = result.sort_values("_is_fav", ascending=False).drop(columns=["_is_fav"])

    # ── 件数サマリ ───────────────────────────
    total_stock = len(df[df["売上フラグ"].fillna("").astype(str).str.strip() == ""])
    if show_all:
        st.caption(f"表示: {len(result)} 件（全体在庫: {total_stock} 件）")
    else:
        st.caption(f"在庫あり: {len(result)} 件 ／ 総データ: {len(df)} 件　※売済等は非表示")

    if len(result) > 200:
        st.warning("200件以上のため最初の200件を表示します。検索条件を絞ってください。")
        result = result.head(200)

    if result.empty:
        st.info("該当する商品がありません。")
        return

    st.divider()

    # ── ヘッダー行 ───────────────────────────
    # 列幅: ⭐ | ID | ブランド | モデル | カラー | 店舗 | 下代 | 上代 | フラグ▼ | 年▼ | 月▼ | メモ
    COL_W = [0.4, 0.7, 1.4, 2.2, 1.4, 0.7, 0.9, 1.0, 1.2, 0.7, 0.7, 1.8]
    HEADERS = ["⭐","ID","ブランド","モデル","カラー","店舗","下代","上代(税込)","フラグ","年","月","メモ"]
    h = st.columns(COL_W)
    for col, label in zip(h, HEADERS):
        col.markdown(f"**{label}**")
    st.divider()

    # ── データ行 ────────────────────────────
    today  = date.today()
    years  = list(range(today.year, today.year - 6, -1))
    months = list(range(1, 13))

    for row_idx, row in result.iterrows():
        flag  = str(row.get("売上フラグ", "")).strip()
        brand = str(row.get("ブランド", "")).strip()
        is_fav = brand in fav_brands
        row_class = _ROW_CLASS.get(flag, "row-stock")

        # ⑥ 行全体に網掛けHTMLコンテナ（開始）
        st.markdown(f'<div class="{row_class}">', unsafe_allow_html=True)

        c = st.columns(COL_W)

        # ⭐
        c[0].write("⭐" if is_fav else "")

        # 基本情報
        c[1].write(str(row.get("ID", "")))
        c[2].write(brand)
        c[3].write(str(row.get("モデル", "")))
        c[4].write(str(row.get("カラー", "")))
        c[5].write(str(row.get("店舗", "")))

        # 価格
        def fmt_price(val):
            try:
                return f"¥{int(float(val)):,}"
            except Exception:
                return "―"

        c[6].write(fmt_price(row.get("下代", "")))
        c[7].write(fmt_price(row.get("上代（税込）", "")))

        # ① フラグ変更プルダウン
        cur_flag_idx = FLAG_OPTIONS.index(flag) if flag in FLAG_OPTIONS else 0
        sel_flag = c[8].selectbox(
            "フラグ",
            options=FLAG_OPTIONS,
            index=cur_flag_idx,
            format_func=lambda x: FLAG_LABELS_DISPLAY.get(x, x),
            key=f"flag_sel_{row_idx}",
            label_visibility="collapsed",
        )
        # 変更検知 → 即保存
        if sel_flag != flag:
            _apply_flag(df, row_idx, sel_flag, row)

        # 年・月ドロップダウン
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

        # 年月変更（〇のときのみ更新ボタン表示）
        if sel_flag == "〇" and (sel_year != cur_year or sel_month != cur_month):
            if c[9].button("↑保存", key=f"ymupd_{row_idx}", help="年月を更新"):
                updated = D.update_flag(df.copy(), row_idx, "〇", year=sel_year, month=sel_month)
                D.save(updated)
                st.success(f"ID {row.get('ID','')} 年月を {sel_year}/{sel_month} に更新しました")
                st.rerun()

        # ② メモ欄（備考列）
        cur_memo = str(row.get("備考", "")) if str(row.get("備考", "")) not in ["nan", "None"] else ""
        new_memo = c[11].text_input(
            "メモ",
            value=cur_memo,
            key=f"memo_{row_idx}",
            label_visibility="collapsed",
            placeholder="メモ...",
        )
        if new_memo != cur_memo:
            updated = df.copy()
            updated.at[row_idx, "備考"] = new_memo
            D.save(updated)
            st.rerun()

        # ⑥ 行コンテナ閉じ
        st.markdown("</div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  フラグ適用（即時保存）
# ─────────────────────────────────────────────
def _apply_flag(df: pd.DataFrame, idx: int, flag: str, row):
    updated = D.update_flag(df.copy(), idx, flag)
    D.save(updated)
    label = D.FLAG_LABELS.get(flag, flag)
    st.success(f"ID {row.get('ID','')} → {label} に更新しました")
    st.rerun()
