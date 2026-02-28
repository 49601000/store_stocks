"""
data.py
GSheets 接続・読み書き・キャッシュを一元管理するデータレイヤー。
他のモジュールはすべてここの関数を使う。
"""

import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date

# ─────────────────────────────────────────────
#  定数
# ─────────────────────────────────────────────
FLAG_LABELS = {
    "〇": "売上済み",
    "△": "スタッフ用",
    "▲": "返品",
    "×": "破棄",
    "":  "在庫あり",
}

STORES = ["ニコメ", "マトイ"]

# ─────────────────────────────────────────────
#  接続
# ─────────────────────────────────────────────
@st.cache_resource
def get_conn():
    return st.connection("gsheets", type=GSheetsConnection)

# ─────────────────────────────────────────────
#  読み込み
# ─────────────────────────────────────────────
@st.cache_data(ttl=60)
def load() -> pd.DataFrame:
    conn = get_conn()
    df = conn.read(usecols=list(range(15)), ttl=60)
    df.columns = df.columns.str.strip()
    if "売上フラグ" in df.columns:
        df["売上フラグ"] = df["売上フラグ"].fillna("").astype(str).str.strip()
    return df

# ─────────────────────────────────────────────
#  書き込み
# ─────────────────────────────────────────────
def save(df: pd.DataFrame):
    """スプレッドシート全体を上書きしてキャッシュをクリア"""
    conn = get_conn()
    conn.update(data=df)
    st.cache_data.clear()

# ─────────────────────────────────────────────
#  ヘルパー：フラグ更新
# ─────────────────────────────────────────────
def update_flag(df: pd.DataFrame, idx: int, flag: str,
                year: int = None, month: int = None) -> pd.DataFrame:
    df.at[idx, "売上フラグ"] = flag
    if flag == "〇":
        today = date.today()
        df.at[idx, "売上年"]  = year  if year  else today.year
        df.at[idx, "売上月"]  = month if month else today.month
    else:
        df.at[idx, "売上年"]  = ""
        df.at[idx, "売上月"]  = ""
    return df

# ─────────────────────────────────────────────
#  ヘルパー：店間移動
# ─────────────────────────────────────────────
def transfer_item(df: pd.DataFrame, idx: int,
                  from_store: str, to_store: str) -> pd.DataFrame:
    today_str = date.today().strftime("%Y-%m-%d")
    df.at[idx, "店舗"]   = to_store
    df.at[idx, "移動元"] = from_store
    df.at[idx, "移動先"] = to_store
    df.at[idx, "移動日"] = today_str
    return df
