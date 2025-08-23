# company_app_final.py
"""
Private Listing App - Final (Search button + non-duplicated filters + dark-green highlight + smoother UX)
Features:
- Search button (form-based) for both modules (fixed first-click "old query" bug)
- Top "quick filters" stay; table-level filters exclude duplicates like BANK/STATE
- Column filters above the table (selects & sliders)
- Pagination + selectable page size
- Match highlighting (HTML, DARK GREEN) and "Matched In" column explaining why a row appears
- History (last 50) + Pins (save/apply/remove)
- CSV / Excel download
- Responsive UI for desktop & mobile
- Password protection via st.secrets['password'] (fallback provided)
Dependencies: streamlit, pandas, matplotlib, openpyxl
"""

from __future__ import annotations
import io
import math
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple, Iterable

import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

# -----------------------------
# App config and CSS
# -----------------------------
st.set_page_config(page_title="Private Listing App", page_icon="☁", layout="wide")

# Custom CSS: dark neon look, mobile-friendly
st.markdown(
    """
    <style>
    .stApp { background-color: #0d001a; }
    h1, h2, h3, h4 { color: #FFD700; font-family: 'Trebuchet MS', sans-serif; font-weight: 700; text-shadow: 0 0 6px #FF0000; }
    .search-input .stTextInput>div>div>input { background: rgba(255,255,255,0.04) !important; border:1px solid #FFD700 !important; color:#FFD700 !important; border-radius:10px !important; padding:10px !important; }
    .stButton>button { background: linear-gradient(45deg,#ff0040,#ff8000) !important; color:white !important; font-weight:700 !important; border-radius:8px !important; }
    .table-filter-row { background: rgba(255,255,255,0.03); border: 1px dashed rgba(255,215,0,0.12); padding:10px; border-radius:8px; margin-bottom:10px; }
    .sidebar .stButton>button { width:100% !important; }
    /* CHANGED: match highlight to DARK GREEN instead of yellow */
    mark { background:#0f7a3a; color:#ffffff; padding:0 2px; border-radius:3px; }
    @media(max-width:600px){
        .stButton>button { padding:8px 10px !important; font-size:14px !important; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# Password (use Streamlit Secrets in production)
# -----------------------------
DEFAULT_PASSWORD = "NIHIL IS GREAT"
PASSWORD = st.secrets.get("password", DEFAULT_PASSWORD)


def require_password() -> None:
    """Simple password gate. Stores flag in session_state."""
    if "password_ok" not in st.session_state:
        st.session_state["password_ok"] = False

    if not st.session_state["password_ok"]:
        st.markdown("<h2 style='text-align:center'>🔐 Protected App</h2>", unsafe_allow_html=True)
        with st.form("pw_form"):
            p = st.text_input("Enter password", type="password", key="pw_input")
            submitted = st.form_submit_button("Unlock")
            if submitted:
                if p == PASSWORD:
                    st.session_state["password_ok"] = True
                    st.success("✅ Access granted")
                else:
                    st.error("❌ Incorrect password")
        if not st.session_state["password_ok"]:
            st.stop()


require_password()

# -----------------------------
# Load data (cached)
# -----------------------------
@st.cache_data(show_spinner=False)
def load_company_data() -> pd.DataFrame:
    try:
        df1 = pd.read_excel("company_listings_part1.xlsx")
        df2 = pd.read_excel("company_listings_part2.xlsx")
    except FileNotFoundError as e:
        st.error(f"Missing company dataset: {e}")
        return pd.DataFrame()
    df = pd.concat([df1, df2], ignore_index=True)
    df.columns = [c.strip().upper().replace(" ", "_") for c in df.columns]
    return df


@st.cache_data(show_spinner=False)
def load_pincode_data() -> pd.DataFrame:
    try:
        df = pd.read_excel("pincode_listings.xlsx")
    except FileNotFoundError as e:
        st.error(f"Missing pincode dataset: {e}")
        return pd.DataFrame()
    df.columns = [c.strip().upper().replace(" ", "_") for c in df.columns]
    return df


COMPANY_DF = load_company_data()
PINCODE_DF = load_pincode_data()

# -----------------------------
# Session state defaults
# -----------------------------
def set_default(k: str, v: Any):
    if k not in st.session_state:
        st.session_state[k] = v

# Company
set_default("company_query", "")
set_default("company_bank", "All")
set_default("company_category", "All")
set_default("company_page", 0)
set_default("company_page_size", 20)
set_default("company_history", [])
set_default("company_pins", [])
# NEW: separate controlled form field key (fixes "first submit shows old query" bug)
set_default("company_form_q", st.session_state["company_query"])

# Pincode
set_default("pincode_query", "")
set_default("pincode_bank", "All")
set_default("pincode_state", "All")
set_default("pincode_page", 0)
set_default("pincode_page_size", 20)
set_default("pincode_history", [])
set_default("pincode_pins", [])
# NEW: separate controlled form field key
set_default("pincode_form_q", st.session_state["pincode_query"])

# -----------------------------
# Small utilities
# -----------------------------
def rerun():
    try:
        st.experimental_rerun()
    except Exception:
        pass


@dataclass
class HistEntry:
    query: str
    bank: str
    cat_state: str
    results: int
    scope: str  # "company" or "pincode"

    def row(self) -> Dict[str, Any]:
        return {
            "Query": self.query or "(none)",
            "Bank": self.bank,
            "Category/State": self.cat_state,
            "Results": int(self.results),
            "Scope": self.scope,
        }


def add_history(key: str, e: HistEntry, limit: int = 50):
    lst = st.session_state.get(key, [])
    row = e.row()
    if not lst or lst[0] != row:
        lst.insert(0, row)
    st.session_state[key] = lst[:limit]


def add_pin(key: str, e: HistEntry, limit: int = 50):
    pins = st.session_state.get(key, [])
    row = e.row()
    if row not in pins:
        pins.insert(0, row)
    st.session_state[key] = pins[:limit]


def paginate(df: pd.DataFrame, page_key: str, size_key: str) -> Tuple[pd.DataFrame, int, int, int]:
    total = len(df)
    page_size = max(1, int(st.session_state[size_key]))
    pages = max(1, math.ceil(total / page_size))
    st.session_state[page_key] = min(st.session_state.get(page_key, 0), pages - 1)
    cur = st.session_state[page_key]
    start = cur * page_size
    end = start + page_size
    return df.iloc[start:end], total, cur, pages


def download_buttons(df: pd.DataFrame, csv_name: str, xlsx_name: str):
    if df.empty:
        return
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    excel_io = io.BytesIO()
    df.to_excel(excel_io, index=False, engine="openpyxl")
    excel_io.seek(0)
    c1, c2 = st.columns([1, 1])
    with c1:
        st.download_button("⬇ Download CSV", data=csv_bytes, file_name=csv_name, mime="text/csv")
    with c2:
        st.download_button("⬇ Download Excel", data=excel_io, file_name=xlsx_name, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# -----------------------------
# Highlight helpers (dark-green)
# -----------------------------
def _normalize(s: Any) -> str:
    return "" if pd.isna(s) else str(s)

def highlight_match(text: Any, query: str) -> str:
    """Wrap exact substring hits of the query in <mark> (dark green)."""
    s = _normalize(text)
    q = _normalize(query).strip()
    if not q:
        return s
    pattern = re.escape(q)
    return re.sub(pattern, lambda m: f"<mark>{m.group(0)}</mark>", s, flags=re.IGNORECASE)

def matched_in(row: pd.Series, q: str, cols: Iterable[str]) -> List[str]:
    """Return list of columns where query occurs (case-insensitive, substring)."""
    ql = q.strip().lower()
    if not ql:
        return []
    hits = []
    for c in cols:
        if c in row and ql in _normalize(row[c]).lower():
            hits.append(c)
    return hits

def build_substring_mask(df: pd.DataFrame, cols: Iterable[str], q: str) -> pd.Series:
    """Vectorized OR across columns for substring matches (faster & stable)."""
    if not q:
        return pd.Series(True, index=df.index)  # no filter
    ql = str(q).lower()
    mask = pd.Series(False, index=df.index)
    for c in cols:
        if c in df.columns:
            col = df[c].astype(str).str.lower()
            mask = mask | col.str.contains(ql, regex=False, na=False)
    return mask

# -----------------------------
# Sidebar: navigation + quick stats + history preview
# -----------------------------
with st.sidebar:
    st.title("📂 Navigation")
    menu = st.radio("Choose Feature", ["🏢 Company Listing Checker", "📮 Pincode Listing Checker", "📊 Dashboard", "ℹ About App"], index=0)

    st.markdown("---")
    st.subheader("📈 Quick stats")
    st.metric("Companies", f"{len(COMPANY_DF):,}")
    st.metric("Pincodes", f"{len(PINCODE_DF):,}")
    st.markdown("---")
    st.subheader("🕒 Recent (preview)")
    preview = []
    if st.session_state.company_history:
        preview.extend(st.session_state.company_history[:3])
    if st.session_state.pincode_history:
        preview.extend(st.session_state.pincode_history[:3])
    if preview:
        st.dataframe(pd.DataFrame(preview), use_container_width=True, height=180)
    else:
        st.info("No history yet")

# -----------------------------
# Helper: in-table filters UI (above table) with exclude list
# -----------------------------
def table_filters(df: pd.DataFrame, key_prefix: str, exclude_cols: Iterable[str] = ()) -> pd.DataFrame:
    """
    Shows up to 6 filters chosen heuristically:
    up to 4 categorical/object columns + up to 2 numeric columns.
    Columns in exclude_cols are skipped so we don't duplicate top-level filters.
    Returns filtered dataframe.
    """
    if df.empty:
        return df

    exclude = {c.upper() for c in exclude_cols}
    cols = [c for c in df.columns if c.upper() not in exclude]

    obj_cols = [c for c in cols if df[c].dtype == object or pd.api.types.is_categorical_dtype(df[c])]
    num_cols = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]
    picked = (obj_cols[:4] + num_cols[:2])[:6]

    st.markdown("<div class='table-filter-row'>", unsafe_allow_html=True)
    if picked:
        per_row = 3
        rows = math.ceil(len(picked) / per_row)
        idx = 0
        for _ in range(rows):
            cols_ui = st.columns(per_row)
            for col_ui in cols_ui:
                if idx >= len(picked):
                    break
                cname = picked[idx]
                idx += 1
                if cname in obj_cols:
                    options = ["All"] + sorted([str(x) for x in df[cname].dropna().unique()])
                    sel = col_ui.selectbox(cname, options, index=0, key=f"{key_prefix}_sel_{cname}")
                    if sel != "All":
                        df = df[df[cname].astype(str) == sel]
                else:
                    mini = float(pd.to_numeric(df[cname], errors="coerce").min())
                    maxi = float(pd.to_numeric(df[cname], errors="coerce").max())
                    if math.isfinite(mini) and math.isfinite(maxi):
                        step = (maxi - mini) / 100 if maxi > mini else 1.0
                        rng = col_ui.slider(
                            cname, min_value=mini, max_value=maxi, value=(mini, maxi),
                            step=step, key=f"{key_prefix}_rng_{cname}"
                        )
                        df = df[
                            (pd.to_numeric(df[cname], errors="coerce") >= rng[0]) &
                            (pd.to_numeric(df[cname], errors="coerce") <= rng[1])
                        ]
                    else:
                        col_ui.write(f"{cname} (no numeric range)")
    st.markdown("</div>", unsafe_allow_html=True)
    return df

# =========================================================
# COMPANY MODULE
# =========================================================
if menu == "🏢 Company Listing Checker":
    st.title("☁🏦 Company Listing Search")

    # Search form with button (BUGFIX: use dedicated form key and DO NOT pass `value=`; rely on session_state key)
    with st.form("company_search_form", clear_on_submit=False):
        q_input = st.text_input(
            "Search text (company name, bank or category):",
            key="company_form_q",
            help="Type and press Search."
        )
        c1, c2 = st.columns([1,1])
        with c1:
            search_button = st.form_submit_button("🔍 Search")
        with c2:
            reset_button = st.form_submit_button("♻ Reset")

    if search_button:
        # persist input -> query used for filtering
        st.session_state.company_query = st.session_state.company_form_q
        st.session_state.company_page = 0
    if reset_button:
        st.session_state.company_form_q = ""
        st.session_state.company_query = ""
        st.session_state.company_page = 0

    # Quick filters (top-level, keep these)
    banks = ["All"] + (sorted(COMPANY_DF["BANK_NAME"].dropna().unique().tolist()) if not COMPANY_DF.empty else ["All"])
    cats = ["All"] + (sorted(COMPANY_DF["COMPANY_CATEGORY"].dropna().unique().tolist()) if not COMPANY_DF.empty else ["All"])
    c1, c2, c3 = st.columns([2, 2, 1])
    with c1:
        bank_choice = st.selectbox("🏦 Bank", banks,
                                   index=(banks.index(st.session_state.company_bank) if st.session_state.company_bank in banks else 0),
                                   key="company_bank_main")
        if bank_choice != st.session_state.company_bank:
            st.session_state.company_bank = bank_choice
            st.session_state.company_page = 0
    with c2:
        cat_choice = st.selectbox("📂 Category", cats,
                                  index=(cats.index(st.session_state.company_category) if st.session_state.company_category in cats else 0),
                                  key="company_cat_main")
        if cat_choice != st.session_state.company_category:
            st.session_state.company_category = cat_choice
            st.session_state.company_page = 0
    with c3:
        size_choice = st.selectbox("Rows", [10, 20, 50, 100],
                                   index=[10, 20, 50, 100].index(st.session_state.company_page_size),
                                   key="company_size_main")
        if size_choice != st.session_state.company_page_size:
            st.session_state.company_page_size = size_choice
            st.session_state.company_page = 0

    # Apply filtering (on raw data)
    results = COMPANY_DF.copy()
    q = st.session_state.company_query.strip()
    search_cols = [c for c in ["COMPANY_NAME", "BANK_NAME", "COMPANY_CATEGORY"] if c in results.columns]

    if not results.empty:
        # Vectorized mask (faster)
        mask = build_substring_mask(results, search_cols, q)
        results = results[mask]
        if st.session_state.company_bank != "All":
            results = results[results["BANK_NAME"].astype(str) == st.session_state.company_bank]
        if st.session_state.company_category != "All":
            results = results[results["COMPANY_CATEGORY"].astype(str) == st.session_state.company_category]

    # In-table filters but exclude duplicates already used above
    results = table_filters(
        results,
        key_prefix="company_table",
        exclude_cols=("BANK_NAME", "COMPANY_CATEGORY", "COMPANY_NAME")
    )

    # Save to history automatically if any filter is active
    if st.session_state.company_query or st.session_state.company_bank != "All" or st.session_state.company_category != "All":
        add_history(
            "company_history",
            HistEntry(
                query=st.session_state.company_query,
                bank=st.session_state.company_bank,
                cat_state=st.session_state.company_category,
                results=len(results),
                scope="company"
            )
        )

    st.success(f"✅ Found {len(results)} matching result(s)")

    # PAGINATION first (PERF: we only highlight current page to avoid lag)
    page_df_raw, total, cur, pages = paginate(results, "company_page", "company_page_size")

    # Prepare display copy for the page only (with highlights and matched-in)
    if not page_df_raw.empty and q:
        display_page = page_df_raw.copy()
        display_page["MATCHED_IN"] = display_page.apply(lambda r: ", ".join(matched_in(r, q, search_cols)) or "-", axis=1)
        for c in search_cols:
            display_page[c] = display_page[c].apply(lambda x: highlight_match(x, q))
        # Render as HTML so highlights show
        st.markdown("### Results")
        st.markdown(display_page.to_html(escape=False, index=False), unsafe_allow_html=True)
    else:
        st.dataframe(page_df_raw, use_container_width=True)

    # Pagination controls
    p1, p2, p3, p4, p5 = st.columns([1, 2, 2, 2, 1])
    with p1:
        if st.button("⏮ First", key="company_first") and cur > 0:
            st.session_state.company_page = 0
            rerun()
    with p2:
        if st.button("⬅ Prev", key="company_prev") and cur > 0:
            st.session_state.company_page = cur - 1
            rerun()
    with p3:
        st.markdown(f"**Page {cur+1} / {pages}**")
    with p4:
        if st.button("Next ➡", key="company_next") and cur < pages - 1:
            st.session_state.company_page = cur + 1
            rerun()
    with p5:
        if st.button("Last ⏭", key="company_last") and cur < pages - 1:
            st.session_state.company_page = pages - 1
            rerun()

    # Downloads use the raw filtered results (without HTML)
    download_buttons(results, "company_results.csv", "company_results.xlsx")

    # Sidebar: pins & history management for company
    with st.sidebar:
        st.markdown("---")
        st.subheader("📌 Company Pins & History")
        if st.button("📌 Pin current", key="pin_company"):
            add_pin(
                "company_pins",
                HistEntry(
                    query=st.session_state.company_query,
                    bank=st.session_state.company_bank,
                    cat_state=st.session_state.company_category,
                    results=len(results),
                    scope="company",
                ),
            )
            rerun()
        if st.button("🧹 Clear Company History", key="clear_company_hist"):
            st.session_state.company_history = []
            rerun()

        st.markdown("**Pins**")
        if st.session_state.company_pins:
            for i, p in enumerate(st.session_state.company_pins):
                with st.expander(f"{i+1}. {p['Query']} | {p['Bank']} | {p['Category/State']} ({p['Results']})"):
                    ca, cb = st.columns(2)
                    with ca:
                        if st.button("Apply", key=f"apply_company_pin_{i}"):
                            st.session_state.company_form_q = p["Query"] if p["Query"] != "(none)" else ""
                            st.session_state.company_query = st.session_state.company_form_q
                            st.session_state.company_bank = p["Bank"]
                            st.session_state.company_category = p["Category/State"]
                            st.session_state.company_page = 0
                            rerun()
                    with cb:
                        if st.button("Remove", key=f"remove_company_pin_{i}"):
                            st.session_state.company_pins.pop(i)
                            rerun()
        else:
            st.write("No pins yet")

        st.markdown("**History (recent)**")
        if st.session_state.company_history:
            st.dataframe(pd.DataFrame(st.session_state.company_history).head(10), use_container_width=True, height=200)
        else:
            st.write("No history yet")

# =========================================================
# PINCODE MODULE
# =========================================================
elif menu == "📮 Pincode Listing Checker":
    st.title("📮🏦 Pincode Listing Search")

    # Search form with button (BUGFIX pattern)
    with st.form("pincode_search_form", clear_on_submit=False):
        q2_input = st.text_input(
            "Search text (pincode, location or state):",
            key="pincode_form_q",
            help="Type and press Search."
        )
        c1, c2 = st.columns([1,1])
        with c1:
            search_button2 = st.form_submit_button("🔍 Search")
        with c2:
            reset_button2 = st.form_submit_button("♻ Reset")

    if search_button2:
        st.session_state.pincode_query = st.session_state.pincode_form_q
        st.session_state.pincode_page = 0
    if reset_button2:
        st.session_state.pincode_form_q = ""
        st.session_state.pincode_query = ""
        st.session_state.pincode_page = 0

    banks = ["All"] + (sorted(PINCODE_DF["BANK"].dropna().unique().tolist()) if not PINCODE_DF.empty else ["All"])
    states = ["All"] + (sorted(PINCODE_DF["STATE"].dropna().unique().tolist()) if not PINCODE_DF.empty else ["All"])
    p1, p2, p3 = st.columns([2, 2, 1])
    with p1:
        bank_choice = st.selectbox("🏦 Bank", banks,
                                   index=(banks.index(st.session_state.pincode_bank) if st.session_state.pincode_bank in banks else 0),
                                   key="pincode_bank_main")
        if bank_choice != st.session_state.pincode_bank:
            st.session_state.pincode_bank = bank_choice
            st.session_state.pincode_page = 0
    with p2:
        state_choice = st.selectbox("🌍 State", states,
                                    index=(states.index(st.session_state.pincode_state) if st.session_state.pincode_state in states else 0),
                                    key="pincode_state_main")
        if state_choice != st.session_state.pincode_state:
            st.session_state.pincode_state = state_choice
            st.session_state.pincode_page = 0
    with p3:
        size_choice = st.selectbox("Rows", [10, 20, 50, 100],
                                   index=[10, 20, 50, 100].index(st.session_state.pincode_page_size),
                                   key="pincode_size_main")
        if size_choice != st.session_state.pincode_page_size:
            st.session_state.pincode_page_size = size_choice
            st.session_state.pincode_page = 0

    results2 = PINCODE_DF.copy()
    q2 = st.session_state.pincode_query.strip()
    search_cols2 = [c for c in ["PINCODE", "LOCATION", "STATE"] if c in results2.columns]

    if not results2.empty:
        mask2 = build_substring_mask(results2, search_cols2, q2)
        results2 = results2[mask2]
        if st.session_state.pincode_bank != "All":
            results2 = results2[results2["BANK"].astype(str) == st.session_state.pincode_bank]
        if st.session_state.pincode_state != "All":
            results2 = results2[results2["STATE"].astype(str) == st.session_state.pincode_state]

    # Table filters excluding duplicates used above
    results2 = table_filters(
        results2,
        key_prefix="pincode_table",
        exclude_cols=("BANK", "STATE", "PINCODE")  # keep LOCATION available
    )

    if st.session_state.pincode_query or st.session_state.pincode_bank != "All" or st.session_state.pincode_state != "All":
        add_history(
            "pincode_history",
            HistEntry(
                query=st.session_state.pincode_query,
                bank=st.session_state.pincode_bank,
                cat_state=st.session_state.pincode_state,
                results=len(results2),
                scope="pincode"
            )
        )

    st.success(f"✅ Found {len(results2)} matching result(s)")

    # Pagination first (PERF: highlight only current page)
    page_df2_raw, total2, cur2, pages2 = paginate(results2, "pincode_page", "pincode_page_size")

    if not page_df2_raw.empty and q2:
        display_page2 = page_df2_raw.copy()
        display_page2["MATCHED_IN"] = display_page2.apply(lambda r: ", ".join(matched_in(r, q2, search_cols2)) or "-", axis=1)
        for c in search_cols2:
            display_page2[c] = display_page2[c].apply(lambda x: highlight_match(x, q2))
        st.markdown("### Results")
        st.markdown(display_page2.to_html(escape=False, index=False), unsafe_allow_html=True)
    else:
        st.dataframe(page_df2_raw, use_container_width=True)

    p1, p2, p3, p4, p5 = st.columns([1, 2, 2, 2, 1])
    with p1:
        if st.button("⏮ First", key="pincode_first") and cur2 > 0:
            st.session_state.pincode_page = 0
            rerun()
    with p2:
        if st.button("⬅ Prev", key="pincode_prev") and cur2 > 0:
            st.session_state.pincode_page = cur2 - 1
            rerun()
    with p3:
        st.markdown(f"**Page {cur2+1} / {pages2}**")
    with p4:
        if st.button("Next ➡", key="pincode_next") and cur2 < pages2 - 1:
            st.session_state.pincode_page = cur2 + 1
            rerun()
    with p5:
        if st.button("Last ⏭", key="pincode_last") and cur2 < pages2 - 1:
            st.session_state.pincode_page = pages2 - 1
            rerun()

    download_buttons(results2, "pincode_results.csv", "pincode_results.xlsx")

    with st.sidebar:
        st.markdown("---")
        st.subheader("📌 Pincode Pins & History")
        if st.button("📌 Pin current", key="pin_pincode"):
            add_pin(
                "pincode_pins",
                HistEntry(
                    query=st.session_state.pincode_query,
                    bank=st.session_state.pincode_bank,
                    cat_state=st.session_state.pincode_state,
                    results=len(results2),
                    scope="pincode",
                ),
            )
            rerun()
        if st.button("🧹 Clear Pincode History", key="clear_pincode_hist"):
            st.session_state.pincode_history = []
            rerun()

        st.markdown("**Pins**")
        if st.session_state.pincode_pins:
            for i, p in enumerate(st.session_state.pincode_pins):
                with st.expander(f"{i+1}. {p['Query']} | {p['Bank']} | {p['Category/State']} ({p['Results']})"):
                    ca, cb = st.columns(2)
                    with ca:
                        if st.button("Apply", key=f"apply_pincode_pin_{i}"):
                            st.session_state.pincode_form_q = p["Query"] if p["Query"] != "(none)" else ""
                            st.session_state.pincode_query = st.session_state.pincode_form_q
                            st.session_state.pincode_bank = p["Bank"]
                            st.session_state.pincode_state = p["Category/State"]
                            st.session_state.pincode_page = 0
                            rerun()
                    with cb:
                        if st.button("Remove", key=f"remove_pincode_pin_{i}"):
                            st.session_state.pincode_pins.pop(i)
                            rerun()
        else:
            st.write("No pins yet")

        st.markdown("**History (recent)**")
        if st.session_state.pincode_history:
            st.dataframe(pd.DataFrame(st.session_state.pincode_history).head(10), use_container_width=True, height=200)
        else:
            st.write("No history yet")

# -----------------------------
# DASHBOARD
# -----------------------------
elif menu == "📊 Dashboard":
    st.title("📊 Dashboard")
    if COMPANY_DF.empty or PINCODE_DF.empty:
        st.info("Load the datasets (Excel) to see visualizations.")
    else:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Companies by Bank (top 20)")
            bc = COMPANY_DF["BANK_NAME"].value_counts().sort_values(ascending=False).head(20)
            fig, ax = plt.subplots()
            bc.plot(kind="bar", ax=ax)
            ax.set_ylabel("Count")
            st.pyplot(fig)
        with c2:
            st.subheader("Companies by Category")
            cc = COMPANY_DF["COMPANY_CATEGORY"].value_counts()
            fig, ax = plt.subplots()
            cc.plot(kind="pie", autopct="%1.1f%%", ax=ax)
            ax.set_ylabel("")
            st.pyplot(fig)
        st.markdown("---")
        st.subheader("Pincode sample")
        st.dataframe(PINCODE_DF.head(25), use_container_width=True)

# -----------------------------
# ABOUT
# -----------------------------
else:
    st.title("ℹ About")
    st.markdown(
        """
        Private Listing App — search button, non-duplicated filters, DARK-GREEN highlight-on-match,
        pagination, history, and pins.
        - Use Streamlit Secrets for password on Streamlit Cloud.
        - Make sure `company_listings_part1.xlsx`, `company_listings_part2.xlsx`, and `pincode_listings.xlsx` are present.
        """
    )
    st.markdown("Made for mobile & desktop (responsive Streamlit layout).")
