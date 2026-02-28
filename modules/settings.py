"""
settings.py
設定タブ：
  1. お気に入りブランド登録（検索タブで最上部に優先表示）
  2. ブランドフィルタ（表示するブランドの許可リスト）

session_state キー:
  "fav_brands"     : set  お気に入りブランド
  "allowed_brands" : set  表示許可ブランド（空 = 全表示）
"""

import streamlit as st
import pandas as pd

SESSION_FAV     = "fav_brands"
SESSION_ALLOWED = "allowed_brands"

# ─────────────────────────────────────────────
#  セッション初期化（app.py 起動時に呼ぶ）
# ─────────────────────────────────────────────
def init(df: pd.DataFrame):
    all_brands = _get_all_brands(df)
    if SESSION_FAV not in st.session_state:
        st.session_state[SESSION_FAV] = set()
    if SESSION_ALLOWED not in st.session_state:
        st.session_state[SESSION_ALLOWED] = set(all_brands)  # 初期は全表示

# ─────────────────────────────────────────────
#  外部参照用ゲッター
# ─────────────────────────────────────────────
def get_fav_brands() -> set:
    """お気に入りブランドを返す"""
    return st.session_state.get(SESSION_FAV, set())

def get_allowed_brands() -> set:
    """表示許可ブランドを返す（空集合 = 全許可）"""
    return st.session_state.get(SESSION_ALLOWED, set())

# ─────────────────────────────────────────────
#  内部ヘルパー
# ─────────────────────────────────────────────
def _get_all_brands(df: pd.DataFrame) -> list:
    if "ブランド" not in df.columns:
        return []
    return sorted(df["ブランド"].dropna().astype(str).str.strip().unique().tolist())

# ─────────────────────────────────────────────
#  タブ描画
# ─────────────────────────────────────────────
def render(df: pd.DataFrame):
    st.subheader("⚙️ 設定")

    all_brands  = _get_all_brands(df)
    fav         = st.session_state.get(SESSION_FAV, set())
    allowed     = st.session_state.get(SESSION_ALLOWED, set(all_brands))
    total       = len(all_brands)
    fav_count   = len([b for b in all_brands if b in fav])
    active_count= len([b for b in all_brands if b in allowed])

    # ══════════════════════════════════════════
    #  セクション1: お気に入りブランド
    # ══════════════════════════════════════════
    st.markdown("### ⭐ お気に入りブランド")
    st.caption(
        f"登録数: {fav_count} ブランド　"
        "｜ お気に入り登録したブランドは検索タブで**最上部に優先表示**されます。"
    )

    # 現在のお気に入り表示＋削除
    if fav:
        fav_sorted = sorted([b for b in all_brands if b in fav])
        st.markdown("**現在のお気に入り:**")
        rm_cols = st.columns(min(len(fav_sorted), 4))
        for i, brand in enumerate(fav_sorted):
            if rm_cols[i % 4].button(f"⭐ {brand}　✕", key=f"rm_fav_{brand}",
                                      help=f"{brand} をお気に入りから外す"):
                st.session_state[SESSION_FAV].discard(brand)
                st.rerun()
    else:
        st.info("お気に入りはまだ登録されていません。下のリストから ⭐ を押して登録してください。")

    st.divider()

    # ══════════════════════════════════════════
    #  セクション2: ブランドフィルタ（許可リスト）
    # ══════════════════════════════════════════
    st.markdown("### 🏷️ ブランドフィルタ（検索タブに表示するブランド）")
    st.caption(f"全 {total} ブランド中　表示ON: {active_count} ブランド")

    # 一括操作
    qa, qb, _ = st.columns([1, 1, 4])
    if qa.button("✅ 全てON"):
        st.session_state[SESSION_ALLOWED] = set(all_brands)
        st.rerun()
    if qb.button("⬜ 全てOFF"):
        st.session_state[SESSION_ALLOWED] = set()
        st.rerun()

    st.divider()

    # ブランド一覧（⭐ ボタン + 表示ON/OFFチェック、3列）
    st.markdown("**⭐ = お気に入り登録　｜　チェック = 検索タブに表示**")

    new_allowed = set()
    new_fav     = set(fav)  # コピー

    cols = st.columns(3)
    for i, brand in enumerate(all_brands):
        is_fav     = brand in fav
        is_allowed = brand in allowed
        col        = cols[i % 3]

        c1, c2 = col.columns([0.15, 0.85])

        # ⭐ お気に入りトグルボタン
        fav_icon = "⭐" if is_fav else "☆"
        if c1.button(fav_icon, key=f"fav_btn_{brand}", help="お気に入り登録/解除"):
            if is_fav:
                new_fav.discard(brand)
            else:
                new_fav.add(brand)
            st.session_state[SESSION_FAV] = new_fav
            st.rerun()

        # 表示ON/OFFチェックボックス
        if c2.checkbox(brand, value=is_allowed, key=f"allow_chk_{brand}"):
            new_allowed.add(brand)

    # チェックボックスの変更を反映
    if new_allowed != allowed:
        st.session_state[SESSION_ALLOWED] = new_allowed
        st.rerun()

    st.divider()
    st.caption("※ 設定はページを閉じるとリセットされます。将来的にスプレッドシートへの保存機能を追加予定。")
