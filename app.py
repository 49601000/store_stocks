import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date

# ─────────────────────────────────────────────
#  ページ設定
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="ニコメ・マトイ 在庫管理",
    page_icon="👓",
    layout="wide",
)

# ─────────────────────────────────────────────
#  スタイル（視認性向上）
# ─────────────────────────────────────────────
st.markdown("""
<style>
    .flag-badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 4px;
        font-weight: bold;
        font-size: 1.1rem;
    }
    .flag-sold   { background:#d4edda; color:#155724; }
    .flag-staff  { background:#fff3cd; color:#856404; }
    .flag-return { background:#f8d7da; color:#721c24; }
    .flag-discard{ background:#e2e3e5; color:#383d41; }
    .flag-stock  { background:#cce5ff; color:#004085; }
    .stButton>button { width: 100%; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  定数
# ─────────────────────────────────────────────
FLAG_LABELS = {
    "〇": "売上済み",
    "△": "スタッフ用",
    "▲": "返品",
    "×": "破棄",
    "": "在庫あり",
}
STORES = ["ニコメ", "マトイ"]

# ─────────────────────────────────────────────
#  GSheets 接続 & データ読み込み
# ─────────────────────────────────────────────
@st.cache_resource
def get_conn():
    return st.connection("gsheets", type=GSheetsConnection)

conn = get_conn()

@st.cache_data(ttl=60)
def load_data():
    df = conn.read(usecols=list(range(15)), ttl=60)
    df.columns = df.columns.str.strip()
    # 売上フラグの NaN → 空文字（在庫あり）
    if "売上フラグ" in df.columns:
        df["売上フラグ"] = df["売上フラグ"].fillna("").astype(str).str.strip()
    return df

def reload():
    """キャッシュを破棄して再読込"""
    st.cache_data.clear()

def write_data(df: pd.DataFrame):
    conn.update(data=df)
    reload()

# ─────────────────────────────────────────────
#  ヘルパー：フラグ更新
# ─────────────────────────────────────────────
def update_flag(df: pd.DataFrame, idx: int, flag: str) -> pd.DataFrame:
    df.at[idx, "売上フラグ"] = flag
    if flag == "〇":
        today = date.today()
        df.at[idx, "売上年"] = today.year
        df.at[idx, "売上月"] = today.month
    else:
        # 売上以外はクリア
        df.at[idx, "売上年"] = ""
        df.at[idx, "売上月"] = ""
    return df

# ─────────────────────────────────────────────
#  ヘルパー：店間移動
# ─────────────────────────────────────────────
def transfer_item(df: pd.DataFrame, idx: int, from_store: str, to_store: str) -> pd.DataFrame:
    today_str = date.today().strftime("%Y-%m-%d")
    df.at[idx, "店舗"]   = to_store
    df.at[idx, "移動元"] = from_store
    df.at[idx, "移動先"] = to_store
    df.at[idx, "移動日"] = today_str
    return df

# ─────────────────────────────────────────────
#  メインUI
# ─────────────────────────────────────────────
st.title("👓 ニコメ・マトイ 在庫管理システム")

with st.spinner("データ読み込み中..."):
    df = load_data()

if df is None or df.empty:
    st.error("データを読み込めませんでした。Secretsとスプレッドシート設定を確認してください。")
    st.stop()

tabs = st.tabs(["🔍 検索・更新", "🔄 店間移動", "📊 ダッシュボード"])

# ══════════════════════════════════════════════
#  TAB 1: 検索・フラグ更新
# ══════════════════════════════════════════════
with tabs[0]:
    st.subheader("在庫検索 & フラグ更新")

    col_a, col_b, col_c, col_d = st.columns([1, 2, 2, 1])
    with col_a:
        search_id = st.text_input("ID 検索", placeholder="例: 1234")
    with col_b:
        search_model = st.text_input("モデル名", placeholder="例: Ray-Ban RX5368")
    with col_c:
        search_color = st.text_input("カラー", placeholder="例: マットブラック")
    with col_d:
        show_all = st.toggle("売済も表示", value=False)

    # フィルタリング
    result = df.copy()

    # ★ デフォルトは在庫あり（空白）のみ
    if not show_all:
        result = result[result["売上フラグ"].fillna("").astype(str).str.strip() == ""]

    if search_id.strip():
        result = result[result["ID"].astype(str).str.contains(search_id.strip(), case=False, na=False)]
    if search_model.strip():
        result = result[result["モデル"].astype(str).str.contains(search_model.strip(), case=False, na=False)]
    if search_color.strip():
        result = result[result["カラー"].astype(str).str.contains(search_color.strip(), case=False, na=False)]

    # 件数表示
    total_stock = len(df[df["売上フラグ"].fillna("").astype(str).str.strip() == ""])
    if show_all:
        st.caption(f"表示中: 全件 {len(result)} 件（うち在庫あり {total_stock} 件）")
    else:
        st.caption(f"在庫あり: {len(result)} 件 ／ 総データ {len(df)} 件　※売済・スタッフ用等は非表示")

    if len(result) > 200:
        st.warning("件数が多いため、最初の 200 件を表示します。検索条件を絞ってください。")
        result = result.head(200)

    # 結果表示 + フラグ操作ボタン
    for row_idx, row in result.iterrows():
        flag = str(row.get("売上フラグ", ""))
        flag_class = {
            "〇": "flag-sold",
            "△": "flag-staff",
            "▲": "flag-return",
            "×": "flag-discard",
        }.get(flag, "flag-stock")
        flag_label = FLAG_LABELS.get(flag, "在庫あり")

        with st.expander(
            f"ID: {row.get('ID','')} ｜ {row.get('ブランド','')} {row.get('モデル','')} {row.get('カラー','')} ｜ 店舗: {row.get('店舗','')}",
            expanded=False,
        ):
            info_col, btn_col = st.columns([3, 2])
            with info_col:
                st.markdown(
                    f"**フラグ:** <span class='flag-badge {flag_class}'>{flag if flag else '（在庫あり）'} {flag_label}</span>",
                    unsafe_allow_html=True,
                )
                st.write(f"上代: ¥{row.get('上代（税込）', ''):,}　売上年月: {row.get('売上年','')} / {row.get('売上月','')}　店舗: {row.get('店舗','')}")

            with btn_col:
                st.write("**フラグ変更:**")
                bc1, bc2, bc3, bc4 = st.columns(4)
                def make_flag_button(col, flag_val, label):
                    if col.button(label, key=f"flag_{row_idx}_{flag_val}"):
                        updated = update_flag(df.copy(), row_idx, flag_val)
                        write_data(updated)
                        st.success(f"ID {row.get('ID','')} → {label} に更新しました")
                        st.rerun()
                make_flag_button(bc1, "〇", "〇 売上")
                make_flag_button(bc2, "△", "△ スタッフ")
                make_flag_button(bc3, "▲", "▲ 返品")
                make_flag_button(bc4, "×", "× 破棄")

# ══════════════════════════════════════════════
#  TAB 2: 店間移動
# ══════════════════════════════════════════════
with tabs[1]:
    st.subheader("🔄 店間移動（ニコメ ⇄ マトイ）")

    st.markdown("""
    移動したい商品の **ID** を入力し、移動方向を選んでボタンを押してください。  
    スプレッドシートの「店舗」「移動元」「移動先」「移動日」が自動更新されます。
    """)

    t_col1, t_col2 = st.columns([1, 2])
    with t_col1:
        transfer_id_input = st.text_input("移動対象 ID", placeholder="例: 5678", key="transfer_id")

    # ID 入力時にプレビュー表示
    target_rows = pd.DataFrame()
    if transfer_id_input.strip():
        target_rows = df[df["ID"].astype(str).str.strip() == transfer_id_input.strip()]

    if not target_rows.empty:
        for row_idx, row in target_rows.iterrows():
            current_store = str(row.get("店舗", ""))
            other_store   = "マトイ" if current_store == "ニコメ" else "ニコメ"

            st.info(
                f"**ID {row.get('ID','')}** ｜ {row.get('ブランド','')} {row.get('モデル','')} {row.get('カラー','')}  \n"
                f"現在の店舗: **{current_store}**　→　移動先: **{other_store}**"
            )

            confirm = st.checkbox(f"上記を確認しました（ID: {row.get('ID','')}）", key=f"confirm_{row_idx}")

            btn_label = f"✅ {current_store} → {other_store} へ移動する"
            if st.button(btn_label, key=f"transfer_{row_idx}", disabled=not confirm):
                updated_df = transfer_item(df.copy(), row_idx, current_store, other_store)
                write_data(updated_df)
                st.success(f"ID {row.get('ID','')} を {other_store} へ移動しました（移動日: {date.today()}）")
                st.rerun()

    elif transfer_id_input.strip():
        st.warning("該当する ID が見つかりませんでした。")

    # 移動履歴表示
    st.divider()
    st.subheader("📋 移動履歴（移動日あり）")
    if "移動日" in df.columns:
        history = df[df["移動日"].notna() & (df["移動日"].astype(str).str.strip() != "")].copy()
        if not history.empty:
            show_cols = [c for c in ["ID","ブランド","モデル","カラー","店舗","移動元","移動先","移動日"] if c in history.columns]
            st.dataframe(
                history[show_cols].sort_values("移動日", ascending=False).reset_index(drop=True),
                use_container_width=True,
            )
        else:
            st.info("移動履歴はまだありません。")
    else:
        st.warning("「移動日」列がスプレッドシートに存在しません。列名を確認してください。")

# ══════════════════════════════════════════════
#  TAB 3: ダッシュボード
# ══════════════════════════════════════════════
with tabs[2]:
    st.subheader("📊 在庫・売上ダッシュボード")

    # --- 在庫サマリ ---
    total      = len(df)
    in_stock   = len(df[df["売上フラグ"].fillna("") == ""])
    sold       = len(df[df["売上フラグ"].fillna("") == "〇"])
    staff      = len(df[df["売上フラグ"].fillna("") == "△"])
    returned   = len(df[df["売上フラグ"].fillna("") == "▲"])
    discarded  = len(df[df["売上フラグ"].fillna("") == "×"])

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("総データ数",    total)
    m2.metric("在庫あり（空白）", in_stock)
    m3.metric("売上済み（〇）",  sold)
    m4.metric("スタッフ用（△）", staff)
    m5.metric("返品（▲）",      returned)

    st.divider()

    d1, d2 = st.columns(2)

    with d1:
        st.markdown("#### 店舗別 在庫数")
        if "店舗" in df.columns:
            store_stock = (
                df[df["売上フラグ"].fillna("") == ""]
                .groupby("店舗")
                .size()
                .reset_index(name="在庫数")
            )
            st.bar_chart(store_stock.set_index("店舗"))
        else:
            st.info("「店舗」列が見つかりません。")

    with d2:
        st.markdown("#### ブランド別 在庫数 TOP20")
        if "ブランド" in df.columns:
            brand_stock = (
                df[df["売上フラグ"].fillna("") == ""]
                .groupby("ブランド")
                .size()
                .sort_values(ascending=False)
                .head(20)
                .reset_index(name="在庫数")
            )
            st.bar_chart(brand_stock.set_index("ブランド"))
        else:
            st.info("「ブランド」列が見つかりません。")

    st.divider()

    d3, d4 = st.columns(2)

    with d3:
        st.markdown("#### 月別 売上数（今年）")
        if "売上年" in df.columns and "売上月" in df.columns:
            current_year = date.today().year
            sold_df = df[
                (df["売上フラグ"] == "〇") &
                (df["売上年"].astype(str).str.strip() == str(current_year))
            ].copy()
            if not sold_df.empty:
                monthly = (
                    sold_df.groupby("売上月")
                    .size()
                    .reset_index(name="売上数")
                    .sort_values("売上月")
                )
                monthly["売上月"] = monthly["売上月"].astype(str) + "月"
                st.bar_chart(monthly.set_index("売上月"))
            else:
                st.info("今年の売上データがありません。")
        else:
            st.info("「売上年」「売上月」列が見つかりません。")

    with d4:
        st.markdown("#### 店舗別 売上数")
        if "店舗" in df.columns:
            store_sold = (
                df[df["売上フラグ"] == "〇"]
                .groupby("店舗")
                .size()
                .reset_index(name="売上数")
            )
            st.bar_chart(store_sold.set_index("店舗"))
        else:
            st.info("「店舗」列が見つかりません。")

    # 生データビュー
    st.divider()
    with st.expander("📄 全データを表示（デバッグ用）"):
        st.dataframe(df, use_container_width=True)

# ─────────────────────────────────────────────
#  フッター
# ─────────────────────────────────────────────
st.divider()
col_f1, col_f2 = st.columns([3, 1])
col_f1.caption("ニコメ・マトイ 在庫管理システム v1.0 | Powered by Streamlit + Google Sheets")
if col_f2.button("🔄 データを再読み込み"):
    reload()
    st.rerun()
