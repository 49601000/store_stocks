"""
dashboard.py
在庫・売上ダッシュボードタブ
"""

import streamlit as st
import pandas as pd
from datetime import date


def render(df: pd.DataFrame):
    st.subheader("📊 在庫・売上ダッシュボード")

    total     = len(df)
    in_stock  = len(df[df["売上フラグ"].fillna("") == ""])
    sold      = len(df[df["売上フラグ"].fillna("") == "〇"])
    staff     = len(df[df["売上フラグ"].fillna("") == "△"])
    returned  = len(df[df["売上フラグ"].fillna("") == "▲"])

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("総データ数",      total)
    m2.metric("在庫あり",        in_stock)
    m3.metric("売上済み（〇）",   sold)
    m4.metric("スタッフ用（△）",  staff)
    m5.metric("返品（▲）",       returned)

    st.divider()
    d1, d2 = st.columns(2)

    with d1:
        st.markdown("#### 店舗別 在庫数")
        if "店舗" in df.columns:
            s = df[df["売上フラグ"].fillna("") == ""].groupby("店舗").size().reset_index(name="在庫数")
            st.bar_chart(s.set_index("店舗"))

    with d2:
        st.markdown("#### ブランド別 在庫数 TOP20")
        if "ブランド" in df.columns:
            b = (df[df["売上フラグ"].fillna("") == ""]
                 .groupby("ブランド").size().sort_values(ascending=False)
                 .head(20).reset_index(name="在庫数"))
            st.bar_chart(b.set_index("ブランド"))

    st.divider()
    d3, d4 = st.columns(2)

    with d3:
        st.markdown("#### 月別 売上数（今年）")
        if "売上年" in df.columns and "売上月" in df.columns:
            cur_year = date.today().year
            sold_df  = df[(df["売上フラグ"] == "〇") &
                          (df["売上年"].astype(str).str.strip() == str(cur_year))]
            if not sold_df.empty:
                m = sold_df.groupby("売上月").size().reset_index(name="売上数").sort_values("売上月")
                m["売上月"] = m["売上月"].astype(str) + "月"
                st.bar_chart(m.set_index("売上月"))
            else:
                st.info("今年の売上データがありません。")

    with d4:
        st.markdown("#### 店舗別 売上数")
        if "店舗" in df.columns:
            ss = df[df["売上フラグ"] == "〇"].groupby("店舗").size().reset_index(name="売上数")
            st.bar_chart(ss.set_index("店舗"))

    st.divider()
    with st.expander("📄 全データを表示（デバッグ用）"):
        st.dataframe(df, use_container_width=True)
