"""
search.py
在庫検索 & フラグ更新タブ。

レイアウト（1行 = 1商品）:
  [ID] [ブランド] [モデル] [カラー] [店舗] [下代] [上代(税込)] │ [フラグボタン×4] [年▼] [月▼]

フィルタ:
  - デフォルト: 在庫あり（売上フラグ空白）のみ
  - トグル: 売済も含む全件表示
  - ラジオ: 店舗（両方 / ニコメのみ / マトイのみ）
  - ブランド: settings.py の許可リストを参照
"""

import streamlit as st
import pandas as pd
from datetime import date
from modules import data as D
from modules.settings import get_allowed_brands, get_fav_brands

# ─────────────────────────────────────────────
#  CSS（フラグバッジ・テーブル風行）
# ─────────────────────────────────────────────
_CSS = """
<style>
.item-row {
    display: flex;
    align-items: center;
    padding: 6px 8px;
    border-bottom: 1px solid #e0e0e0;
    font-size: 0.85rem;
    gap: 8px;
}
.item-row:hover { background: #f5f9ff; }
.badge {
    display: inline-block;
    padding: 1px 7px;
    border-radius: 3px;
    font-weight: bold;
    font-size: 0.8rem;
    white-space: nowrap;
}
.badge-stock   { background:#cce5ff; color:#004085; }
.badge-sold    { background:#d4edda; color:#155724; }
.badge-staff   { background:#fff3cd; color:#856404; }
.badge-return  { background:#f8d7da; color:#721c24; }
.badge-discard { background:#e2e3e5; color:#383d41; }
</style>
"""

FLAG_BADGE = {
    "〇": ("badge-sold",    "〇 売上"),
    "△": ("badge-staff",   "△ スタッフ"),
    "▲": ("badge-return",  "▲ 返品"),
    "×": ("badge-discard", "× 破棄"),
    "":  ("badge-stock",   "在庫"),
}

# ─────────────────────────────────────────────
#  メイン描画
# ─────────────────────────────────────────────
def render(df: pd.DataFrame):
    st.markdown(_CSS, unsafe_allow_html=True)
    st.subheader("在庫検索 & フラグ更新")

    # ── フィルタ行 ───────────────────────────
    fa, fb, fc, fd, fe, ff = st.columns([1, 2, 2, 1.5, 1.5, 1])
    with fa:
        search_id = st.text_input("ID", placeholder="例: 1234", label_visibility="collapsed",
                                  help="ID検索")
        st.caption("🔎 ID")
    with fb:
        search_model = st.text_input("モデル", placeholder="モデル名", label_visibility="collapsed")
        st.caption("📋 モデル")
    with fc:
        search_color = st.text_input("カラー", placeholder="カラー", label_visibility="collapsed")
        st.caption("🎨 カラー")
    with fd:
        store_filter = st.radio("店舗", ["両方", "ニコメ", "マトイ"],
                                horizontal=True, label_visibility="collapsed")
        st.caption("🏪 店舗")
    with fe:
        show_all = st.toggle("売済も表示", value=False)
    with ff:
        st.write("")  # スペーサー

    # ── データフィルタリング ──────────────────
    result = df.copy()

    # 1) 在庫あり絞り込み（デフォルト）
    if not show_all:
        result = result[result["売上フラグ"].fillna("").astype(str).str.strip() == ""]

    # 2) 店舗フィルタ
    if store_filter != "両方" and "店舗" in result.columns:
        result = result[result["店舗"].astype(str).str.strip() == store_filter]

    # 3) ブランドフィルタ（設定タブの許可リスト）
    allowed_brands = get_allowed_brands()
    if allowed_brands and "ブランド" in result.columns:
        result = result[result["ブランド"].astype(str).str.strip().isin(allowed_brands)]

    # 4) テキスト検索
    if search_id.strip():
        result = result[result["ID"].astype(str).str.contains(search_id.strip(), case=False, na=False)]
    if search_model.strip():
        result = result[result["モデル"].astype(str).str.contains(search_model.strip(), case=False, na=False)]
    if search_color.strip():
        result = result[result["カラー"].astype(str).str.contains(search_color.strip(), case=False, na=False)]

    # 5) お気に入りブランドを先頭に並び替え
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
    h = st.columns([0.5, 0.8, 1.5, 2.5, 1.5, 0.8, 1.0, 1.0, 2.5, 0.8, 0.8])
    for col, label in zip(h, ["⭐","ID","ブランド","モデル","カラー","店舗","下代","上代(税込)","フラグ変更","年","月"]):
        col.markdown(f"**{label}**")

    st.divider()

    # ── データ行 ────────────────────────────
    today = date.today()
    years  = list(range(today.year, today.year - 5, -1))
    months = list(range(1, 13))

    for row_idx, row in result.iterrows():
        flag = str(row.get("売上フラグ", ""))
        brand = str(row.get("ブランド", "")).strip()
        is_fav = brand in fav_brands

        c = st.columns([0.5, 0.8, 1.5, 2.5, 1.5, 0.8, 1.0, 1.0, 2.5, 0.8, 0.8])

        # ⭐ お気に入りインジケーター
        c[0].write("⭐" if is_fav else "")

        # 基本情報列
        c[1].write(str(row.get("ID", "")))
        c[2].write(brand)
        c[3].write(str(row.get("モデル", "")))
        c[4].write(str(row.get("カラー", "")))
        c[5].write(str(row.get("店舗", "")))

        # 価格列（数値変換してカンマ区切り）
        def fmt_price(val):
            try:
                return f"¥{int(float(val)):,}"
            except Exception:
                return str(val) if str(val) not in ["", "nan"] else "―"

        c[6].write(fmt_price(row.get("下代", "")))
        c[7].write(fmt_price(row.get("上代（税込）", "")))

        # フラグ変更ボタン（4つ横並び）
        with c[8]:
            b1, b2, b3, b4 = st.columns(4)
            if b1.button("〇", key=f"s_{row_idx}_maru",    help="売上済みにする"):
                _apply_flag(df, row_idx, "〇", row)
            if b2.button("△", key=f"s_{row_idx}_sankaku", help="スタッフ用にする"):
                _apply_flag(df, row_idx, "△", row)
            if b3.button("▲", key=f"s_{row_idx}_kuro",    help="返品にする"):
                _apply_flag(df, row_idx, "▲", row)
            if b4.button("×", key=f"s_{row_idx}_batsu",   help="破棄にする"):
                _apply_flag(df, row_idx, "×", row)

        # 年・月ドロップダウン（売上〇のときだけ有効）
        cur_year  = row.get("売上年", "")
        cur_month = row.get("売上月", "")
        try:
            yi = years.index(int(float(cur_year))) if str(cur_year) not in ["", "nan"] else 0
        except Exception:
            yi = 0
        try:
            mi = months.index(int(float(cur_month))) if str(cur_month) not in ["", "nan"] else today.month - 1
        except Exception:
            mi = today.month - 1

        sel_year  = c[9].selectbox("年",  years,  index=yi, key=f"yr_{row_idx}", label_visibility="collapsed")
        sel_month = c[10].selectbox("月", months, index=mi, key=f"mo_{row_idx}", label_visibility="collapsed")

        # 年月変更ボタン（売上フラグが〇の行のみ表示）
        if flag == "〇":
            if c[9].button("更新", key=f"ymupd_{row_idx}", help="年月を更新"):
                updated = D.update_flag(df.copy(), row_idx, "〇", year=sel_year, month=sel_month)
                D.save(updated)
                st.success(f"ID {row.get('ID','')} の年月を {sel_year}/{sel_month} に更新しました")
                st.rerun()

# ─────────────────────────────────────────────
#  フラグ適用（即時保存）
# ─────────────────────────────────────────────
def _apply_flag(df: pd.DataFrame, idx: int, flag: str, row):
    updated = D.update_flag(df.copy(), idx, flag)
    D.save(updated)
    label = D.FLAG_LABELS.get(flag, flag)
    st.success(f"ID {row.get('ID','')} → {label} に更新しました")
    st.rerun()
