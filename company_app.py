import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import io
from datetime import datetime

# =========================
# 🔐 App & Auth Settings
# =========================
PASSWORD = "NIHIL IS GREAT"  # change if needed
APP_TITLE = "Private Company Listing App"
DATA_FILE = "company_listings.xlsx.xlsx"  # your file in repo root

# Columns we search & optionally highlight (UPPERCASE after cleaning)
SEARCHABLE_COLS = ["COMPANY_NAME", "BANK_NAME", "COMPANY_CATEGORY"]

# =========================
# ⚙️ Streamlit Page Config
# =========================
st.set_page_config(page_title=APP_TITLE, page_icon="☁️", layout="wide")

# =========================
# 🎨 Custom CSS (neon/dark)
# =========================
st.markdown(
    """
    <style>
        .stApp { background-color: #0d001a; }
        h1, h2, h3, h4 {
            color: #FFD700; text-align: center;
            font-family: 'Trebuchet MS', sans-serif; font-weight: bold;
            text-shadow: 0px 0px 10px #FF0000;
        }
        .stTextInput > div > div > input, .stSelectbox > div > div {
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid #FFD700;
            border-radius: 10px; color: #FFD700 !important;
            padding: 8px; font-size: 16px;
        }
        .stDownloadButton button, .stButton button {
            background: linear-gradient(45deg, #ff0040, #ff8000);
            color: white; border-radius: 10px; border: none;
            font-weight: bold; padding: 10px 20px;
            box-shadow: 0 0 15px rgba(255, 0, 0, 0.7);
        }
        .stSidebar { background: #1a001f; }
        /* Highlight mark tag */
        mark { background-color: #ffea00; color: #000; padding: 0 2px; border-radius: 3px; }
        /* Thin golden border */
        .stApp::before {
            content: ""; position: fixed; top: 0; left: 0; right: 0; bottom: 0;
            border: 2px double #FFD700; outline: 1px solid #FF0000;
            pointer-events: none; z-index: 9999;
        }
        /* Narrower dataframe header height */
        div[data-testid="stDataFrame"] div[role="columnheader"]{
            padding-top: 6px; padding-bottom: 6px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================
# 🔒 Password Gate
# =========================
def check_password() -> bool:
    if "password_ok" not in st.session_state:
        st.session_state.password_ok = False

    if not st.session_state.password_ok:
        st.markdown("<h2>🔐 Protected App</h2>", unsafe_allow_html=True)
        pwd = st.text_input("Enter Password", type="password", key="pwd_box")
        col_a, col_b, col_c = st.columns([1,1,4])
        with col_a:
            if st.button("Unlock"):
                if pwd == PASSWORD:
                    st.session_state.password_ok = True
                    st.success("✅ Access Granted")
                else:
                    st.error("❌ Incorrect Password")
                    st.stop()
        st.stop()

    return True

# =========================
# 🧠 Session Defaults
# =========================
def init_session():
    if "history" not in st.session_state:
        st.session_state.history = []  # list of dicts: {query, bank, category, ts, count}
    if "page_number" not in st.session_state:
        st.session_state.page_number = 1
    if "page_size" not in st.session_state:
        st.session_state.page_size = 50
    if "last_query_tuple" not in st.session_state:
        st.session_state.last_query_tuple = ("", "All", "All")
    if "selected_columns" not in st.session_state:
        st.session_state.selected_columns = None  # set later after data is loaded

# =========================
# 📥 Load Data (cached)
# =========================
@st.cache_data
def load_data():
    df = pd.read_excel(DATA_FILE)
    df.columns = [c.strip().upper().replace(" ", "_") for c in df.columns]
    return df

# =========================
# 🖍️ Utilities
# =========================
def highlight_text(s: str, query: str) -> str:
    """Wrap all case-insensitive occurrences of query in <mark>..</mark>."""
    if not isinstance(s, str) or not query:
        return s
    try:
        import re
        pattern = re.compile(re.escape(query), re.IGNORECASE)
        return pattern.sub(lambda m: f"<mark>{m.group(0)}</mark>", s)
    except Exception:
        return s

def apply_filters(df: pd.DataFrame, query: str, bank: str, category: str) -> pd.DataFrame:
    out = df
    if query:
        q = query.lower()
        mask = False
        for col in SEARCHABLE_COLS:
            if col in out.columns:
                mask = mask | out[col].astype(str).str.lower().str.contains(q, regex=False, na=False)
        out = out[mask] if isinstance(mask, pd.Series) else out

    if bank != "All" and "bank_name".upper() in out.columns:
        out = out[out["BANK_NAME"] == bank]
    if category != "All" and "company_category".upper() in out.columns:
        out = out[out["COMPANY_CATEGORY"] == category]
    return out

def paginate_df(df: pd.DataFrame, page_number: int, page_size: int):
    total = len(df)
    if total == 0:
        return df, total, 0, 0
    start = (page_number - 1) * page_size
    end = start + page_size
    return df.iloc[start:end], total, start + 1, min(end, total)

def save_search_to_history(query: str, bank: str, category: str, count: int):
    if not query and bank == "All" and category == "All":
        return  # don't spam empty searches
    entry = {
        "query": query,
        "bank": bank,
        "category": category,
        "count": int(count),
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    st.session_state.history.insert(0, entry)
    # keep only 20
    st.session_state.history = st.session_state.history[:20]

# =========================
# 🚀 App
# =========================
if check_password():
    init_session()

    # Sidebar
    st.sidebar.title("📂 Navigation")
    menu = st.sidebar.radio("Go to", ["🔎 Search", "🕘 History", "📊 Dashboard", "ℹ️ About"])

    # Load once
    data = load_data()

    # column selector defaults
    if st.session_state.selected_columns is None:
        default_cols = [c for c in ["COMPANY_NAME", "BANK_NAME", "COMPANY_CATEGORY"] if c in data.columns]
        st.session_state.selected_columns = default_cols or list(data.columns)[:6]

    # ============
    # 🔎 SEARCH
    # ============
    if menu == "🔎 Search":
        st.title("☁️🏦 Company Listing Search")

        # Filters row (live search)
        top_col1, top_col2, top_col3, top_col4 = st.columns([3, 2, 2, 2])
        with top_col1:
            query = st.text_input("Search (Company / Bank / Category)", placeholder="Type to filter…")
        with top_col2:
            bank_options = ["All"] + sorted(data["BANK_NAME"].dropna().unique().tolist()) if "BANK_NAME" in data.columns else ["All"]
            bank = st.selectbox("🏦 Bank", bank_options)
        with top_col3:
            cat_options = ["All"] + sorted(data["COMPANY_CATEGORY"].dropna().unique().tolist()) if "COMPANY_CATEGORY" in data.columns else ["All"]
            category = st.selectbox("📂 Category", cat_options)
        with top_col4:
            page_size = st.selectbox("Rows / page", [25, 50, 100, 250, 500], index=[25,50,100,250,500].index(st.session_state.page_size) if st.session_state.page_size in [25,50,100,250,500] else 1)
            st.session_state.page_size = page_size

        # If any filter changed, reset to page 1
        current_tuple = (query, bank, category)
        if current_tuple != st.session_state.last_query_tuple:
            st.session_state.page_number = 1
            st.session_state.last_query_tuple = current_tuple

        # Apply filters (LIVE)
        results = apply_filters(data, query, bank, category)
        total = len(results)

        # Column selector
        with st.expander("🧰 Columns to display"):
            available_cols = list(results.columns)
            st.session_state.selected_columns = st.multiselect(
                "Pick columns",
                available_cols,
                default=[c for c in st.session_state.selected_columns if c in available_cols] or available_cols[:6],
            )

        # Pagination controls
        page_df, total_rows, start_i, end_i = paginate_df(results, st.session_state.page_number, st.session_state.page_size)

        info_left, info_right = st.columns(2)
        with info_left:
            st.success(f"✅ {total_rows} match(es) • Showing {start_i}–{end_i}")
        with info_right:
            col_prev, col_page, col_next = st.columns([1,2,1])
            with col_prev:
                if st.button("⬅️ Prev", use_container_width=True, disabled=st.session_state.page_number <= 1):
                    st.session_state.page_number = max(1, st.session_state.page_number - 1)
            with col_page:
                st.number_input("Page", min_value=1, value=st.session_state.page_number, key="page_num_input", step=1)
                st.session_state.page_number = st.session_state.page_num_input
            with col_next:
                max_page = max(1, (total_rows + st.session_state.page_size - 1) // st.session_state.page_size)
                if st.button("Next ➡️", use_container_width=True, disabled=st.session_state.page_number >= max_page):
                    st.session_state.page_number = min(max_page, st.session_state.page_number + 1)

        # Toggle: highlight matches
        hl_col, dl_col, save_col = st.columns([1,1,1])
        with hl_col:
            show_highlight = st.toggle("✨ Highlight matches", value=True, help="Highlight query text in searchable columns")
        with dl_col:
            # Downloads for current filtered results (all rows)
            if total_rows > 0:
                csv = results.to_csv(index=False).encode("utf-8")
                st.download_button("⬇️ Download CSV", data=csv, file_name="results.csv", mime="text/csv", use_container_width=True)
        with save_col:
            if st.button("📌 Save this search", use_container_width=True, disabled=(total_rows == 0 and not query and bank=="All" and category=="All")):
                save_search_to_history(query, bank, category, total_rows)
                st.toast("Saved to history ✅")

        # View: highlighted HTML or interactive dataframe
        if total_rows == 0:
            st.warning("No results. Try a broader query.")
        else:
            if show_highlight and query:
                # Make a copy with highlights only for searchable columns
                view_df = page_df.copy()
                for col in SEARCHABLE_COLS:
                    if col in view_df.columns:
                        view_df[col] = view_df[col].astype(str).apply(lambda s: highlight_text(s, query))
                # Only show selected columns
                cols_to_show = [c for c in st.session_state.selected_columns if c in view_df.columns]
                html = view_df[cols_to_show].to_html(escape=False, index=False)
                st.markdown(html, unsafe_allow_html=True)
                st.caption("Tip: toggle off “Highlight matches” to get sortable headers.")
            else:
                cols_to_show = [c for c in st.session_state.selected_columns if c in page_df.columns]
                st.dataframe(page_df[cols_to_show], use_container_width=True)

    # ============
    # 🕘 HISTORY
    # ============
    elif menu == "🕘 History":
        st.title("🕘 Recent Searches (max 20)")
        if not st.session_state.history:
            st.info("No saved searches yet. Go to **Search** and click **📌 Save this search**.")
        else:
            hist_df = pd.DataFrame(st.session_state.history)
            st.dataframe(hist_df, use_container_width=True)
            st.markdown("---")
            # Re-run a search
            st.subheader("↩️ Re-run a saved search")
            if len(st.session_state.history) > 0:
                labels = [f"[{i+1}] {h['ts']} • “{h['query'] or '—'}” • Bank: {h['bank']} • Category: {h['category']} • {h['count']} hits"
                          for i, h in enumerate(st.session_state.history)]
                choice = st.selectbox("Pick a past search", labels)
                idx = labels.index(choice)
                selected = st.session_state.history[idx]
                if st.button("Load this search"):
                    # set state so Search page picks it up
                    st.session_state.last_query_tuple = (selected["query"], selected["bank"], selected["category"])
                    st.session_state.page_number = 1
                    # simulate filling filters by storing in special keys
                    st.session_state._restore_query = selected["query"]
                    st.session_state._restore_bank = selected["bank"]
                    st.session_state._restore_cat = selected["category"]
                    st.success("Loaded! Go to the 🔎 Search tab.")
            if st.button("🧹 Clear history"):
                st.session_state.history = []
                st.toast("History cleared")

    # ============
    # 📊 DASHBOARD
    # ============
    elif menu == "📊 Dashboard":
        st.title("📊 Company Data Dashboard")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("🏦 Companies by Bank")
            if "BANK_NAME" in data.columns:
                bank_counts = data["BANK_NAME"].value_counts()
                fig, ax = plt.subplots()
                bank_counts.plot(kind="bar", ax=ax, color="crimson")
                ax.set_ylabel("Number of Companies")
                ax.set_title("Companies per Bank")
                st.pyplot(fig)
            else:
                st.info("BANK_NAME column not found.")

        with col2:
            st.subheader("📂 Companies by Category")
            if "COMPANY_CATEGORY" in data.columns:
                category_counts = data["COMPANY_CATEGORY"].value_counts()
                fig, ax = plt.subplots()
                category_counts.plot(kind="pie", autopct="%1.1f%%", ax=ax, colors=plt.cm.Set3.colors)
                ax.set_ylabel("")
                ax.set_title("Company Category Share")
                st.pyplot(fig)
            else:
                st.info("COMPANY_CATEGORY column not found.")

        st.markdown("<hr>", unsafe_allow_html=True)
        st.subheader("📈 Data Snapshot")
        st.dataframe(data.head(20), use_container_width=True)

    # ============
    # ℹ️ ABOUT
    # ============
    elif menu == "ℹ️ About":
        st.title("ℹ️ About this App")
        st.markdown(
            """
            This app is a **private company listing search tool** with a polished UX:

            **Features**
            - 🔐 Secure login (local password)
            - 🔎 Live search (no button)
            - 📑 Pagination with page size
            - ↕️ Sortable table (when highlighting is off)
            - 🖍️ Keyword highlighting (toggle)
            - 🧰 Column selector
            - 🕘 Search history (last 20, re-runnable)
            - 📊 Simple dashboard charts
            - ⬇️ Download filtered results (CSV)

            **Tech**: Streamlit, Pandas, Matplotlib
            """
        )
        st.markdown("<h4 style='text-align: center; color: #FFD700;'>✨ Developed by Nihil ✨</h4>", unsafe_allow_html=True)

    # =========================
    # 🔄 Restore history selection to Search (optional nicety)
    # =========================
    # If user loaded a history entry, prefill on Search page the next time they go there
    if menu == "🔎 Search":
        # apply any requested restore from history (one-time)
        if st.session_state.get("_restore_query") is not None:
            # re-render with restored filters by updating last tuple & clearing restore keys
            st.session_state.last_query_tuple = (
                st.session_state["_restore_query"],
                st.session_state.get("_restore_bank", "All"),
                st.session_state.get("_restore_cat", "All"),
            )
            # Clear restore flags so it doesn't loop
            st.session_state._restore_query = None
            st.session_state._restore_bank = None
            st.session_state._restore_cat = None
