"""
transfer.py
店間移動タブ（ニコメ ⇄ マトイ）
"""

import streamlit as st
import pandas as pd
from datetime import date
from modules import data as D


def render(df: pd.DataFrame):
    st.subheader("🔄 店間移動（ニコメ ⇄ マトイ）")
    st.markdown("移動したい商品の **ID** を入力し、確認後にボタンを押してください。")

    t_col1, _ = st.columns([1, 2])
    with t_col1:
        transfer_id_input = st.text_input("移動対象 ID", placeholder="例: 5678", key="transfer_id")

    if transfer_id_input.strip():
        target_rows = df[df["ID"].astype(str).str.strip() == transfer_id_input.strip()]
    else:
        target_rows = pd.DataFrame()

    if not target_rows.empty:
        for row_idx, row in target_rows.iterrows():
            current_store = str(row.get("店舗", ""))
            other_store   = "マトイ" if current_store == "ニコメ" else "ニコメ"

            st.info(
                f"**ID {row.get('ID','')}** ｜ {row.get('ブランド','')} "
                f"{row.get('モデル','')} {row.get('カラー','')}  \n"
                f"現在の店舗: **{current_store}**　→　移動先: **{other_store}**"
            )

            confirm = st.checkbox(
                f"上記の内容を確認しました（ID: {row.get('ID','')}）",
                key=f"confirm_{row_idx}"
            )
            if st.button(
                f"✅ {current_store} → {other_store} へ移動する",
                key=f"transfer_{row_idx}",
                disabled=not confirm,
            ):
                updated_df = D.transfer_item(df.copy(), row_idx, current_store, other_store)
                D.save(updated_df)
                st.success(f"ID {row.get('ID','')} を {other_store} へ移動しました（{date.today()}）")
                st.rerun()

    elif transfer_id_input.strip():
        st.warning("該当する ID が見つかりませんでした。")

    # 移動履歴
    st.divider()
    st.subheader("📋 移動履歴")
    if "移動日" in df.columns:
        history = df[df["移動日"].notna() & (df["移動日"].astype(str).str.strip() != "")].copy()
        if not history.empty:
            cols = [c for c in ["ID","ブランド","モデル","カラー","店舗","移動元","移動先","移動日"] if c in history.columns]
            st.dataframe(
                history[cols].sort_values("移動日", ascending=False).reset_index(drop=True),
                use_container_width=True,
            )
        else:
            st.info("移動履歴はまだありません。")
    else:
        st.warning("「移動日」列がスプレッドシートに存在しません。")
