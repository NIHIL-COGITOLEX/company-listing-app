import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import io
from math import ceil

# =====================================================
# App Configuration
# =====================================================
st.set_page_config(page_title="Private Listing App", page_icon="☁", layout="wide")

# --- Password (use Streamlit Secrets in production) ---
# 1) In Streamlit Cloud, set in: App → Settings → Secrets
#    [password = "YOUR_STRONG_PASSWORD"]
# 2) Locally, create .streamlit/secrets.toml with the same key.
DEFAULT_PASSWORD = "NIHIL IS GREAT"
PASSWORD = st.secrets.get("password", DEFAULT_PASSWORD)

# =====================================================
# Password Protection
# =====================================================
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    if not st.session_state.password_correct:
        st.markdown("<h2 style='text-align: center;'>🔐 Protected App</h2>", unsafe_allow_html=True)
        pw = st.text_input("Enter Password", type="password", key="login_pw")
        if st.button("Unlock", use_container_width=True):
            if pw == PASSWORD:
                st.session_state.password_correct = True
                st.success("✅ Access Granted")
            else:
                st.error("❌ Incorrect Password")
        st.stop()
    return True

# =====================================================
# Custom CSS Styling
# =====================================================
st.markdown(
    """
<style>
.stApp { background-color: #0d001a; }
h1, h2, h3, h4 { color: #FFD700; text-align: center; font-family: 'Trebuchet MS', sans-serif; font-weight: bold; text-shadow: 0px 0px 10px #FF0000; }
.stTextInput > div > div > input { background: rgba(255, 255, 255, 0.08); border: 1px solid #FFD700; border-radius: 10px; color: #FFD700; padding: 10px; font-size: 16px; }
.stDownloadButton button, .stButton button { background: linear-gradient(45deg, #ff0040, #ff8000); color: white; border-radius: 10px; border: none; font-weight: bold; padding: 10px 20px; box-shadow: 0 0 15px rgba(255, 0, 0, 0.7); }
.stSidebar { background: #1a001f; }
</style>
""",
    unsafe_allow_html=True,
)

# =====================================================
# Data Loaders (cached)
# =====================================================
@st.cache_data(show_spinner=False)
def load_company_data():
    try:
        df1 = pd.read_excel("company_listings_part1.xlsx")
        df2 = pd.read_excel("company_listings_part2.xlsx")
    except FileNotFoundError as e:
        st.error(f"❌ Missing dataset file: {e}")
        st.stop()
    df = pd.concat([df1, df2], ignore_index=True)
    df.columns = [c.strip().upper().replace(" ", "_") for c in df.columns]
    return df

@st.cache_data(show_spinner=False)
def load_pincode_data():
    try:
        df = pd.read_excel("pincode_listings.xlsx")
    except FileNotFoundError as e:
        st.error(f"❌ Missing dataset file: {e}")
        st.stop()
    df.columns = [c.strip().upper().replace(" ", "_") for c in df.columns]
    return df

# =====================================================
# Helpers
# =====================================================
def rerun():
    try:
        st.rerun()
    except Exception:
        st.experimental_rerun()


def normalize_history_entry(entry: dict) -> dict:
    # Ensure identical structure for dedupe
    return {
        "query": entry.get("query", ""),
        "bank": entry.get("bank", "All"),
        "category": entry.get("category", entry.get("state", "All")),
        "results": int(entry.get("results", 0)),
        "scope": entry.get("scope", "company"),
    }


def add_to_history(state_key: str, entry: dict, limit: int = 50):
    entry = normalize_history_entry(entry)
    if state_key not in st.session_state:
        st.session_state[state_key] = []
    # Avoid duplicate immediate entries
    if not st.session_state[state_key] or st.session_state[state_key][0] != entry:
        st.session_state[state_key].insert(0, entry)
    st.session_state[state_key] = st.session_state[state_key][:limit]


def pin_current(state_key: str, entry: dict, limit: int = 50):
    entry = normalize_history_entry(entry)
    if state_key not in st.session_state:
        st.session_state[state_key] = []
    # Prevent duplicates in pins
    if entry not in st.session_state[state_key]:
        st.session_state[state_key].insert(0, entry)
        st.session_state[state_key] = st.session_state[state_key][:limit]


def paginate(df: pd.DataFrame, page_key: str, page_size: int):
    if page_key not in st.session_state:
        st.session_state[page_key] = 0
    total = len(df)
    pages = max(1, ceil(total / page_size))
    current = min(st.session_state[page_key], pages - 1)

    start = current * page_size
    end = start + page_size
    slice_df = df.iloc[start:end]

    c1, c2, c3, c4, c5 = st.columns([1,2,2,2,1])
    with c1:
        if st.button("⏮ First", key=f"{page_key}_first") and current > 0:
            st.session_state[page_key] = 0
            rerun()
    with c2:
        if st.button("⬅ Prev", key=f"{page_key}_prev") and current > 0:
            st.session_state[page_key] = current - 1
            rerun()
    with c3:
        st.markdown(f"**Page {current+1} / {pages}**  ")
    with c4:
        if st.button("Next ➡", key=f"{page_key}_next") and current < pages - 1:
            st.session_state[page_key] = current + 1
            rerun()
    with c5:
        if st.button("Last ⏭", key=f"{page_key}_last") and current < pages - 1:
            st.session_state[page_key] = pages - 1
            rerun()

    st.dataframe(slice_df, use_container_width=True)
    return slice_df, total


# =====================================================
# Main App
# =====================================================
if check_password():
    # Sidebar Navigation
    st.sidebar.title("📂 Navigation")
    menu = st.sidebar.radio(
        "Choose Feature",
        ["🏢 Company Listing Checker", "📮 Pincode Listing Checker", "📊 Dashboard", "ℹ About App"],
        key="nav_menu",
    )

    # -------------------------------------------------
    # Company Listing Checker (Live Search + Pagination + History + Pins)
    # -------------------------------------------------
    if menu == "🏢 Company Listing Checker":
        st.title("☁🏦 Company Listing Search")
        data = load_company_data()

        # --- Sidebar Controls ---
        st.sidebar.markdown("### 🔎 Company Filters")
        if "company_query" not in st.session_state:
            st.session_state.company_query = ""
        if "company_bank" not in st.session_state:
            st.session_state.company_bank = "All"
        if "company_category" not in st.session_state:
            st.session_state.company_category = "All"
        if "company_page_size" not in st.session_state:
            st.session_state.company_page_size = 20

        st.session_state.company_query = st.sidebar.text_input(
            "Search (Company / Bank / Category)",
            value=st.session_state.company_query,
            key="company_query_input",
        )
        st.session_state.company_bank = st.sidebar.selectbox(
            "🏦 Bank",
            ["All"] + sorted(data["BANK_NAME"].dropna().unique()),
            index=(0 if st.session_state.company_bank == "All" else ( ["All"] + sorted(data["BANK_NAME"].dropna().unique()) ).index(st.session_state.company_bank) if st.session_state.company_bank in ["All"] + sorted(data["BANK_NAME"].dropna().unique()) else 0),
            key="company_bank_select",
        )
        st.session_state.company_category = st.sidebar.selectbox(
            "📂 Category",
            ["All"] + sorted(data["COMPANY_CATEGORY"].dropna().unique()),
            index=(0 if st.session_state.company_category == "All" else ( ["All"] + sorted(data["COMPANY_CATEGORY"].dropna().unique()) ).index(st.session_state.company_category) if st.session_state.company_category in ["All"] + sorted(data["COMPANY_CATEGORY"].dropna().unique()) else 0),
            key="company_category_select",
        )
        st.session_state.company_page_size = st.sidebar.selectbox(
            "Rows per page", [10, 20, 50, 100], index=[10,20,50,100].index(st.session_state.company_page_size), key="company_page_size_select"
        )

        # Detect changes to reset page and record history
        current_tuple = (
            st.session_state.company_query,
            st.session_state.company_bank,
            st.session_state.company_category,
        )
        if "company_last" not in st.session_state:
            st.session_state.company_last = current_tuple
        if current_tuple != st.session_state.company_last:
            st.session_state.company_last = current_tuple
            st.session_state["company_page"] = 0

        # --- Live Filtering ---
        results = data.copy()
        q = st.session_state.company_query.strip().lower()
        if q:
            mask = (
                results["COMPANY_NAME"].str.lower().str.contains(q, regex=False, na=False)
                | results["BANK_NAME"].str.lower().str.contains(q, regex=False, na=False)
                | results["COMPANY_CATEGORY"].str.lower().str.contains(q, regex=False, na=False)
            )
            results = results[mask]
        if st.session_state.company_bank != "All":
            results = results[results["BANK_NAME"] == st.session_state.company_bank]
        if st.session_state.company_category != "All":
            results = results[results["COMPANY_CATEGORY"] == st.session_state.company_category]

        # --- History (auto) ---
        if q or st.session_state.company_bank != "All" or st.session_state.company_category != "All":
            add_to_history(
                "company_history",
                {
                    "query": st.session_state.company_query,
                    "bank": st.session_state.company_bank,
                    "category": st.session_state.company_category,
                    "results": len(results),
                    "scope": "company",
                },
            )

        # --- Results + Pagination ---
        st.success(f"✅ Found {len(results)} matching result(s)")
        page_slice, total = paginate(results, "company_page", st.session_state.company_page_size)

        # --- Downloads (full filtered set) ---
        if total > 0:
            csv = results.to_csv(index=False).encode("utf-8")
            excel_buffer = io.BytesIO()
            results.to_excel(excel_buffer, index=False, engine="openpyxl")
            excel_buffer.seek(0)
            st.download_button("⬇ Download Results (CSV)", data=csv, file_name="company_results.csv", mime="text/csv")
            st.download_button(
                "⬇ Download Results (Excel)",
                data=excel_buffer,
                file_name="company_results.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        # --- Sidebar: History & Pins ---
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🕒 Recent Company Searches")
        if "company_history" in st.session_state and st.session_state.company_history:
            hist_df = pd.DataFrame(st.session_state.company_history)
            st.sidebar.dataframe(hist_df.head(10), use_container_width=True)
            if st.sidebar.button("🧹 Clear History", key="clear_company_hist", use_container_width=True):
                st.session_state.company_history = []
                rerun()
        else:
            st.sidebar.info("No search history yet.")

        # Pins
        st.sidebar.markdown("### 📌 Pinned Searches")
        if "company_pins" not in st.session_state:
            st.session_state.company_pins = []
        if st.sidebar.button("📌 Pin current search", key="pin_company", use_container_width=True):
            pin_current(
                "company_pins",
                {
                    "query": st.session_state.company_query,
                    "bank": st.session_state.company_bank,
                    "category": st.session_state.company_category,
                    "results": len(results),
                    "scope": "company",
                },
            )
            rerun()
        # List pins with apply/remove
        for i, pin in enumerate(st.session_state.company_pins):
            with st.sidebar.expander(f"{i+1}. {pin['query'] or '(no query)'} | {pin['bank']} | {pin['category']} ({pin['results']})"):
                cA, cB = st.columns(2)
                with cA:
                    if st.button("Apply", key=f"apply_company_pin_{i}"):
                        st.session_state.company_query = pin["query"]
                        st.session_state.company_bank = pin["bank"]
                        st.session_state.company_category = pin["category"]
                        st.session_state.company_last = (pin["query"], pin["bank"], pin["category"])  # keep page reset clean
                        rerun()
                with cB:
                    if st.button("Remove", key=f"remove_company_pin_{i}"):
                        st.session_state.company_pins.pop(i)
                        rerun()

    # -------------------------------------------------
    # Pincode Listing Checker (Live Search + Pagination + History + Pins)
    # -------------------------------------------------
    elif menu == "📮 Pincode Listing Checker":
        st.title("📮🏦 Pincode Listing Search")
        data = load_pincode_data()

        # --- Sidebar Controls ---
        st.sidebar.markdown("### 🔎 Pincode Filters")
        if "pincode_query" not in st.session_state:
            st.session_state.pincode_query = ""
        if "pincode_bank" not in st.session_state:
            st.session_state.pincode_bank = "All"
        if "pincode_state" not in st.session_state:
            st.session_state.pincode_state = "All"
        if "pincode_page_size" not in st.session_state:
            st.session_state.pincode_page_size = 20

        st.session_state.pincode_query = st.sidebar.text_input(
            "Search (Pincode / Location / State)",
            value=st.session_state.pincode_query,
            key="pincode_query_input",
        )
        st.session_state.pincode_bank = st.sidebar.selectbox(
            "🏦 Bank",
            ["All"] + sorted(data["BANK"].dropna().unique()),
            index=(0 if st.session_state.pincode_bank == "All" else ( ["All"] + sorted(data["BANK"].dropna().unique()) ).index(st.session_state.pincode_bank) if st.session_state.pincode_bank in ["All"] + sorted(data["BANK"].dropna().unique()) else 0),
            key="pincode_bank_select",
        )
        st.session_state.pincode_state = st.sidebar.selectbox(
            "🌍 State",
            ["All"] + sorted(data["STATE"].dropna().unique()),
            index=(0 if st.session_state.pincode_state == "All" else ( ["All"] + sorted(data["STATE"].dropna().unique()) ).index(st.session_state.pincode_state) if st.session_state.pincode_state in ["All"] + sorted(data["STATE"].dropna().unique()) else 0),
            key="pincode_state_select",
        )
        st.session_state.pincode_page_size = st.sidebar.selectbox(
            "Rows per page", [10, 20, 50, 100], index=[10,20,50,100].index(st.session_state.pincode_page_size), key="pincode_page_size_select"
        )

        # Detect changes to reset page and record history
        current_tuple = (
            st.session_state.pincode_query,
            st.session_state.pincode_bank,
            st.session_state.pincode_state,
        )
        if "pincode_last" not in st.session_state:
            st.session_state.pincode_last = current_tuple
        if current_tuple != st.session_state.pincode_last:
            st.session_state.pincode_last = current_tuple
            st.session_state["pincode_page"] = 0

        # --- Live Filtering ---
        results = data.copy()
        q = st.session_state.pincode_query.strip().lower()
        if q:
            mask = (
                results["PINCODE"].astype(str).str.contains(q, regex=False, na=False)
                | results["LOCATION"].str.lower().str.contains(q, regex=False, na=False)
                | results["STATE"].str.lower().str.contains(q, regex=False, na=False)
            )
            results = results[mask]
        if st.session_state.pincode_bank != "All":
            results = results[results["BANK"] == st.session_state.pincode_bank]
        if st.session_state.pincode_state != "All":
            results = results[results["STATE"] == st.session_state.pincode_state]

        # --- History (auto) ---
        if q or st.session_state.pincode_bank != "All" or st.session_state.pincode_state != "All":
            add_to_history(
                "pincode_history",
                {
                    "query": st.session_state.pincode_query,
                    "bank": st.session_state.pincode_bank,
                    "state": st.session_state.pincode_state,
                    "results": len(results),
                    "scope": "pincode",
                },
            )

        # --- Results + Pagination ---
        st.success(f"✅ Found {len(results)} matching result(s)")
        page_slice, total = paginate(results, "pincode_page", st.session_state.pincode_page_size)

        # --- Downloads (full filtered set) ---
        if total > 0:
            csv = results.to_csv(index=False).encode("utf-8")
            excel_buffer = io.BytesIO()
            results.to_excel(excel_buffer, index=False, engine="openpyxl")
            excel_buffer.seek(0)
            st.download_button("⬇ Download Results (CSV)", data=csv, file_name="pincode_results.csv", mime="text/csv")
            st.download_button(
                "⬇ Download Results (Excel)",
                data=excel_buffer,
                file_name="pincode_results.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        # --- Sidebar: History & Pins ---
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🕒 Recent Pincode Searches")
        if "pincode_history" in st.session_state and st.session_state.pincode_history:
            hist_df = pd.DataFrame(st.session_state.pincode_history)
            st.sidebar.dataframe(hist_df.head(10), use_container_width=True)
            if st.sidebar.button("🧹 Clear History", key="clear_pincode_hist", use_container_width=True):
                st.session_state.pincode_history = []
                rerun()
        else:
            st.sidebar.info("No search history yet.")

        st.sidebar.markdown("### 📌 Pinned Searches")
        if "pincode_pins" not in st.session_state:
            st.session_state.pincode_pins = []
        if st.sidebar.button("📌 Pin current search", key="pin_pincode", use_container_width=True):
            pin_current(
                "pincode_pins",
                {
                    "query": st.session_state.pincode_query,
                    "bank": st.session_state.pincode_bank,
                    "state": st.session_state.pincode_state,
                    "results": len(results),
                    "scope": "pincode",
                },
            )
            rerun()
        for i, pin in enumerate(st.session_state.pincode_pins):
            with st.sidebar.expander(f"{i+1}. {pin['query'] or '(no query)'} | {pin['bank']} | {pin['category']} ({pin['results']})" if 'category' in pin else f"{i+1}. {pin['query'] or '(no query)'} | {pin['bank']} | {pin.get('state','')} ({pin['results']})"):
                cA, cB = st.columns(2)
                with cA:
                    if st.button("Apply", key=f"apply_pincode_pin_{i}"):
                        st.session_state.pincode_query = pin["query"]
                        st.session_state.pincode_bank = pin["bank"]
                        st.session_state.pincode_state = pin.get("state", "All")
                        st.session_state.pincode_last = (pin["query"], pin["bank"], pin.get("state", "All"))
                        rerun()
                with cB:
                    if st.button("Remove", key=f"remove_pincode_pin_{i}"):
                        st.session_state.pincode_pins.pop(i)
                        rerun()

    # -------------------------------------------------
    # Dashboard
    # -------------------------------------------------
    elif menu == "📊 Dashboard":
        st.title("📊 Combined Dashboard")
        company_data = load_company_data()
        pincode_data = load_pincode_data()

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🏦 Companies by Bank")
            bank_counts = company_data["BANK_NAME"].value_counts()
            fig, ax = plt.subplots()
            bank_counts.plot(kind="bar", ax=ax)
            ax.set_ylabel("Number of Companies")
            ax.set_title("Companies per Bank")
            st.pyplot(fig)

        with col2:
            st.subheader("📂 Companies by Category")
            category_counts = company_data["COMPANY_CATEGORY"].value_counts()
            fig, ax = plt.subplots()
            category_counts.plot(kind="pie", autopct="%1.1f%%", ax=ax)
            ax.set_ylabel("")
            ax.set_title("Company Category Share")
            st.pyplot(fig)

        st.markdown("<hr>", unsafe_allow_html=True)
        st.subheader("📮 Pincode Data Snapshot")
        st.dataframe(pincode_data.head(20), use_container_width=True)

    # -------------------------------------------------
    # About
    # -------------------------------------------------
    elif menu == "ℹ About App":
        st.title("ℹ About this App")
        st.markdown(
            """
        This app is a *private listing search tool*. 🔑  
        **Now with:**
        - ⚡ Live search (no Search button)
        - 📜 History (up to 50 per module)
        - 📌 Pinned searches (up to 50 per module)
        - 📄 Pagination (10/20/50/100 rows per page)
        - ⬇ Download filtered results as CSV/Excel
        - 🗺 Dashboard charts
        - 🎨 Dark neon UI styling  
        💡 Built with *Streamlit + Pandas + Matplotlib*
        """
        )
        st.markdown("<h4 style='text-align: center; color: #FFD700;'>✨ Developed by Nihil ✨</h4>", unsafe_allow_html=True)
