"""
data.py  v2
GSheets 接続・読み書き・キャッシュ管理

キャッシュ戦略:
  - df本体は st.session_state["_df_cache"] に保持
  - 検索・表示はすべてsession_stateから読む（API不使用）
  - 保存時はAPIに書くが session_state も即更新（再取得しない）
  - TTLは600秒（10分）。手動更新ボタンで任意リフレッシュ可能
  - アプリ起動時の初回のみAPIを叩く
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
    "×": "除外",
    "":  "在庫あり",
}
STORES = ["ニコメ", "マトイ"]

_CACHE_KEY    = "_df_cache"       # session_state キー
_TTL_SECONDS  = 600               # 自動リフレッシュ間隔（秒）

# ─────────────────────────────────────────────
#  接続（アプリ全体で1インスタンス）
# ─────────────────────────────────────────────
@st.cache_resource
def get_conn():
    return st.connection("gsheets", type=GSheetsConnection)

# ─────────────────────────────────────────────
#  APIからの生読み込み（内部用・直接呼ばない）
# ─────────────────────────────────────────────
@st.cache_data(ttl=_TTL_SECONDS, show_spinner="スプレッドシートを読み込み中...")
def _fetch_from_api() -> pd.DataFrame:
    """TTLキャッシュ付きAPI取得。TTL内は何度呼ばれてもAPIを叩かない。"""
    conn = get_conn()
    df = conn.read(usecols=list(range(15)), ttl=_TTL_SECONDS)
    df.columns = df.columns.str.strip()
    if "売上フラグ" in df.columns:
        df["売上フラグ"] = df["売上フラグ"].fillna("").astype(str).str.strip()
    return df

# ─────────────────────────────────────────────
#  公開：データ読み込み
# ─────────────────────────────────────────────
def load() -> pd.DataFrame:
    """
    session_stateにキャッシュがあればそちらを返す。
    なければAPIから取得してsession_stateに保存。
    → 検索・表示操作では一切APIを叩かない。
    """
    if _CACHE_KEY not in st.session_state:
        st.session_state[_CACHE_KEY] = _fetch_from_api().copy()
    return st.session_state[_CACHE_KEY]

# ─────────────────────────────────────────────
#  公開：強制リフレッシュ（手動更新ボタン用）
# ─────────────────────────────────────────────
def force_reload() -> pd.DataFrame:
    """
    TTLキャッシュを破棄してAPIから再取得。
    フッターの「再読み込み」ボタンから呼ぶ。
    """
    st.cache_data.clear()
    if _CACHE_KEY in st.session_state:
        del st.session_state[_CACHE_KEY]
    df = _fetch_from_api().copy()
    st.session_state[_CACHE_KEY] = df
    return df

# ─────────────────────────────────────────────
#  公開：書き込み
# ─────────────────────────────────────────────
def save(df: pd.DataFrame):
    """
    APIに書き込み後、session_stateを即更新。
    TTLキャッシュは破棄しない → 次のload()はsession_stateから高速返却。
    """
    conn = get_conn()
    conn.update(data=df)
    # session_stateを新データで上書き（API再取得なし）
    st.session_state[_CACHE_KEY] = df.copy()

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
