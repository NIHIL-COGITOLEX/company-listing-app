import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import io
import re

# =========================
# 🔐 App & Auth Settings
# =========================
PASSWORD = "NIHIL IS GREAT"
APP_TITLE = "Private Company Listing App"
DATA_FILE = "company_listings.xlsx.xlsx"
SEARCHABLE_COLS = ["COMPANY_NAME", "BANK_NAME", "COMPANY_CATEGORY"]

# =========================
# ⚙ Page Config
# =========================
st.set_page_config(page_title=APP_TITLE, page_icon="☁", layout="wide")

# =========================
# 🎨 Compact, Spacious CSS
# =========================
st.markdown(
    """
    <style>
      /* App background + readable base */
      .stApp { background:#0d001a; }
      html, body, [class*="css"] { font-size:16px; }

      /* Headings: larger + spacing */
      h1,h2,h3 { color:#FFD700; text-align:center; font-family:'Trebuchet MS',sans-serif;
                 text-shadow:0 0 10px #FF0000; margin-top:12px; margin-bottom:18px; }
      h1 { font-size:40px; }
      h2 { font-size:28px; }

      /* Neon inputs/buttons */
      .stTextInput>div>div>input, .stSelectbox>div>div, .stNumberInput input {
        background:rgba(255,255,255,0.08); border:1px solid #FFD700; border-radius:12px;
        color:#FFD700 !important; padding:12px; font-size:16px;
      }
      .stDownloadButton button, .stButton button {
        background:linear-gradient(45deg,#ff0040,#ff8000); color:#fff; border:none;
        border-radius:12px; font-weight:700; padding:12px 20px;
        box-shadow:0 0 18px rgba(255,0,0,.5);
      }

      /* Sidebar polish */
      section[data-testid="stSidebar"] { background:#120021; padding:12px; }

      /* Card-like sections with breathing room */
      .block-container { padding-top:20px; padding-bottom:40px; }
      .spacious { background:rgba(255,255,255,0.03); border:1px solid rgba(255,215,0,0.25);
                  border-radius:18px; padding:22px; margin:14px 0 28px 0;
                  box-shadow:0 6px 30px rgba(255,0,80,0.15); }

      /* Dataframe height + padding */
      div[data-testid="stDataFrame"] { padding:6px 2px; }
      div[data-testid="stDataFrame"] div[role="columnheader"]{ padding-top:10px; padding-bottom:10px; }

      /* Highlight mark tag for HTML tables */
      mark { background:#ffea00; color:#000; padding:0 3px; border-radius:3px; }

      /* Zebra stripes for HTML-rendered table */
      table.zebra { width:100%; border-collapse:separate; border-spacing:0 6px; }
      table.zebra thead th {
        color:#FFD700; text-align:left; padding:10px 12px; font-weight:700;
        background:rgba(255,255,255,0.04); border-bottom:1px solid rgba(255,215,0,0.25);
      }
      table.zebra tbody tr td {
        padding:12px; background:rgba(255,255,255,0.035);
        border-top:1px solid rgba(255,255,255,0.06);
        border-bottom:1px solid rgba(255,255,255,0.06);
      }
      table.zebra tbody tr:nth-child(even) td { background:rgba(255,255,255,0.06); }
      table.zebra tbody tr:hover td { background:rgba(255,255,255,0.09); }

      /* Thin golden frame */
      .stApp::before {
        content:""; position:fixed; inset:0; border:2px double #FFD700; outline:1px solid #FF0000;
        pointer-events:none; z-index:9999; opacity:.6;
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
        cols = st.columns([1,1,4])
        with cols[0]:
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
    ss = st.session_state
    ss.history = ss.get("history", [])           # [{query, bank, category, count, ts}]
    ss.page_number = ss.get("page_number", 1)
    ss.page_size = ss.get("page_size", 50)
    ss.last_query_tuple = ss.get("last_query_tuple", ("", "All", "All"))

# =========================
# 📥 Load Data (cached)
# =========================
@st.cache_data
def load_data():
    df = pd.read_excel(DATA_FILE)
    df.columns = [c.strip().upper().replace(" ", "_") for c in df.columns]
    return df

# =========================
# 🔎 Filter / Paginate
# =========================
def apply_filters(df: pd.DataFrame, query: str, bank: str, category: str) -> pd.DataFrame:
    out = df
    if query:
        q = query.lower()
        mask = False
        for col in SEARCHABLE_COLS:
            if col in out.columns:
                mask = mask | out[col].astype(str).str.lower().str.contains(q, regex=False, na=False)
        out = out[mask] if isinstance(mask, pd.Series) else out
    if bank != "All" and "BANK_NAME" in out.columns:
        out = out[out["BANK_NAME"] == bank]
    if category != "All" and "COMPANY_CATEGORY" in out.columns:
        out = out[out["COMPANY_CATEGORY"] == category]
    return out

def paginate_df(df: pd.DataFrame, page_number: int, page_size: int):
    total = len(df)
    if total == 0:
        return df, total, 0, 0
    start = (page_number - 1) * page_size
    end = start + page_size
    return df.iloc[start:end], total, start + 1, min(end, total)

def highlight_text(text: str, query: str) -> str:
    if not isinstance(text, str) or not query:
        return text
    try:
        pattern = re.compile(re.escape(query), re.IGNORECASE)
        return pattern.sub(lambda m: f"<mark>{m.group(0)}</mark>", text)
    except Exception:
        return text

def save_history(query: str, bank: str, category: str, count: int):
    if not query and bank == "All" and category == "All":
        return
    st.session_state.history.insert(0, {
        "query": query, "bank": bank, "category": category,
        "count": int(count), "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
    st.session_state.history = st.session_state.history[:20]

# =========================
# 🚀 App
# =========================
if check_password():
    init_session()

    st.sidebar.title("📂 Navigation")
    menu = st.sidebar.radio("Go to", ["🔎 Search", "🕘 History", "📊 Dashboard", "ℹ About"])

    data = load_data()

    # ============
    # 🔎 SEARCH
    # ============
    if menu == "🔎 Search":
        st.markdown("<div class='spacious'>", unsafe_allow_html=True)
        st.title("☁🏦 Company Listing Search")

        a,b,c,d = st.columns([3,2,2,2])
        with a:
            query = st.text_input("Search (Company / Bank / Category)", placeholder="Type to filter…")
        with b:
            bank_options = ["All"] + sorted(data["BANK_NAME"].dropna().unique().tolist()) if "BANK_NAME" in data.columns else ["All"]
            bank = st.selectbox("🏦 Bank", bank_options, index=0)
        with c:
            cat_options = ["All"] + sorted(data["COMPANY_CATEGORY"].dropna().unique().tolist()) if "COMPANY_CATEGORY" in data.columns else ["All"]
            category = st.selectbox("📂 Category", cat_options, index=0)
        with d:
            page_size = st.selectbox("Rows / page", [25, 50, 100, 250, 500],
                                     index=[25,50,100,250,500].index(st.session_state.page_size)
                                     if st.session_state.page_size in [25,50,100,250,500] else 1)
            st.session_state.page_size = page_size

        current_tuple = (query, bank, category)
        if current_tuple != st.session_state.last_query_tuple:
            st.session_state.page_number = 1
            st.session_state.last_query_tuple = current_tuple

        results = apply_filters(data, query, bank, category)
        page_df, total_rows, start_i, end_i = paginate_df(results, st.session_state.page_number, st.session_state.page_size)

        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<div class='spacious'>", unsafe_allow_html=True)

        left, right = st.columns([3,2])
        with left:
            st.success(f"✅ {total_rows} match(es) • Showing {start_i}–{end_i}")
        with right:
            p1,p2,p3 = st.columns([1,2,1])
            with p1:
                if st.button("⬅ Prev", use_container_width=True, disabled=st.session_state.page_number <= 1):
                    st.session_state.page_number = max(1, st.session_state.page_number - 1)
            with p2:
                st.number_input("Page", min_value=1, value=st.session_state.page_number, key="page_num_input", step=1)
                st.session_state.page_number = st.session_state.page_num_input
            with p3:
                max_page = max(1, (total_rows + st.session_state.page_size - 1) // st.session_state.page_size)
                if st.button("Next ➡", use_container_width=True, disabled=st.session_state.page_number >= max_page):
                    st.session_state.page_number = min(max_page, st.session_state.page_number + 1)

        t1, t2, t3 = st.columns([1,1,1])
        with t1:
            show_highlight = st.toggle("✨ Highlight matches", value=True, help="Highlight query text in searchable columns")
        with t2:
            if total_rows > 0:
                csv = results.to_csv(index=False).encode("utf-8")
                st.download_button("⬇ Download CSV", data=csv, file_name="results.csv",
                                   mime="text/csv", use_container_width=True)
        with t3:
            if st.button("📌 Save this search", use_container_width=True,
                         disabled=(total_rows == 0 and not query and bank=="All" and category=="All")):
                save_history(query, bank, category, total_rows)
                st.toast("Saved to history ✅")

        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<div class='spacious'>", unsafe_allow_html=True)

        if total_rows == 0:
            st.warning("No results. Try a broader query.")
        else:
            if show_highlight and query:
                view_df = page_df.copy()
                for col in SEARCHABLE_COLS:
                    if col in view_df.columns:
                        view_df[col] = view_df[col].astype(str).apply(lambda s: highlight_text(s, query))
                # Render nice HTML zebra table for readability
                html = "<table class='zebra'><thead><tr>" + "".join(
                    f"<th>{st.escape_html(str(c))}</th>" for c in view_df.columns
                ) + "</tr></thead><tbody>"
                for _, row in view_df.iterrows():
                    html += "<tr>" + "".join(f"<td>{val}</td>" for val in row.values) + "</tr>"
                html += "</tbody></table>"
                st.markdown(html, unsafe_allow_html=True)
                st.caption("Tip: toggle off “Highlight matches” to enable sortable headers.")
            else:
                # Use data_editor (disabled) for built-in sorting + plenty of space
                st.data_editor(
                    page_df,
                    hide_index=True,
                    use_container_width=True,
                    disabled=True,
                    num_rows="dynamic",
                )

        st.markdown("</div>", unsafe_allow_html=True)

    # ============
    # 🕘 HISTORY
    # ============
    elif menu == "🕘 History":
        st.markdown("<div class='spacious'>", unsafe_allow_html=True)
        st.title("🕘 Recent Searches (max 20)")

        if not st.session_state.history:
            st.info("No saved searches yet. Go to *Search* and click *📌 Save this search*.")
        else:
            hist_df = pd.DataFrame(st.session_state.history)
            st.data_editor(hist_df, hide_index=True, use_container_width=True, disabled=True)
            st.markdown("---")
            st.subheader("↩ Re-run a saved search")
            labels = [
                f"[{i+1}] {h['ts']} • “{h['query'] or '—'}” • Bank: {h['bank']} • Category: {h['category']} • {h['count']} hits"
                for i, h in enumerate(st.session_state.history)
            ]
            choice = st.selectbox("Pick a past search", labels) if labels else None
            if choice and st.button("Load this search"):
                idx = labels.index(choice)
                selected = st.session_state.history[idx]
                st.session_state.last_query_tuple = (selected["query"], selected["bank"], selected["category"])
                st.session_state.page_number = 1
                st.session_state._restore_query = selected["query"]
                st.session_state._restore_bank = selected["bank"]
                st.session_state._restore_cat = selected["category"]
                st.success("Loaded! Go to the 🔎 Search tab.")
            if st.button("🧹 Clear history"):
                st.session_state.history = []
                st.toast("History cleared")
        st.markdown("</div>", unsafe_allow_html=True)

    # ============
    # 📊 DASHBOARD
    # ============
    elif menu == "📊 Dashboard":
        st.markdown("<div class='spacious'>", unsafe_allow_html=True)
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
        st.data_editor(data.head(20), hide_index=True, use_container_width=True, disabled=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # ============
    # ℹ ABOUT
    # ============
    elif menu == "ℹ About":
        st.markdown("<div class='spacious'>", unsafe_allow_html=True)
        st.title("ℹ About this App")
        st.markdown(
            """
            This app is a *private company listing search tool* with a polished UX:

            *Features*
            - 🔐 Secure login (local password)
            - 🔎 Live search (no button)
            - 🏦 Bank & 📂 Category filters
            - 📑 Pagination with page size
            - ↕ Sortable table (when highlighting is off)
            - 🖍 Keyword highlighting (toggle)
            - 🕘 Search history (last 20, re-runnable)
            - 📊 Simple dashboard charts
            - ⬇ Download filtered results (CSV)

            *Tech*: Streamlit, Pandas, Matplotlib
            """
        )
        st.markdown("<h4 style='text-align: center; color: #FFD700;'>✨ Developed by Nihil ✨</h4>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # =========================
    # 🔄 Restore (from History) to Search
    # =========================
    if menu == "🔎 Search" and st.session_state.get("_restore_query") is not None:
        st.session_state.last_query_tuple = (
            st.session_state["_restore_query"],
            st.session_state.get("_restore_bank", "All"),
            st.session_state.get("_restore_cat", "All"),
        )
        st.session_state._restore_query = None
        st.session_state._restore_bank = None
        st.session_state._restore_cat = None
