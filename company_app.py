import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import io
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

# ----------------------------
# --- App Configuration ---
# ----------------------------
st.set_page_config(page_title="Private Listing App", page_icon="☁", layout="wide")
PASSWORD = "NIHIL IS GREAT"  # 🔑 Change this if you want


# ----------------------------
# --- Password Protection ---
# ----------------------------
def check_password():
    """Simple password protection using session state"""
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    if not st.session_state.password_correct:
        st.markdown("<h2 style='text-align: center;'>🔐 Protected App</h2>", unsafe_allow_html=True)
        password_input = st.text_input("Enter Password", type="password")

        if st.button("Unlock"):
            if password_input == PASSWORD:
                st.session_state.password_correct = True
                st.success("✅ Access Granted")
            else:
                st.error("❌ Incorrect Password")
                st.stop()
        else:
            st.stop()
    return True


# ----------------------------
# --- Custom CSS Styling ---
# ----------------------------
st.markdown(
    """
    <style>
        .stApp { background-color: #0d001a; }
        h1, h2, h3, h4 {
            color: #FFD700; text-align: center;
            font-family: 'Trebuchet MS', sans-serif; font-weight: bold;
            text-shadow: 0px 0px 10px #FF0000;
        }
        .stTextInput > div > div > input {
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid #FFD700;
            border-radius: 10px; color: #FFD700;
            padding: 10px; font-size: 16px;
        }
        .stDownloadButton button, .stButton button {
            background: linear-gradient(45deg, #ff0040, #ff8000);
            color: white; border-radius: 10px; border: none;
            font-weight: bold; padding: 10px 20px;
            box-shadow: 0 0 15px rgba(255, 0, 0, 0.7);
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ----------------------------
# --- Load Data ---
# ----------------------------
@st.cache_data
def load_company_data():
    df = pd.read_excel("company_listings.xlsx.xlsx")
    df.columns = [c.strip().upper().replace(" ", "_") for c in df.columns]
    return df


@st.cache_data
def load_pincode_data():
    df = pd.read_excel("pincode_listings.xlsx")
    df.columns = [c.strip().upper().replace(" ", "_") for c in df.columns]
    return df


# ----------------------------
# --- AgGrid Renderer ---
# ----------------------------
def render_grid(df: pd.DataFrame, search_query: str, key: str):
    page_size = st.selectbox("Rows per page", [25, 50, 100, 200], index=1, key=f"ps_{key}")

    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_default_column(filter=True, sortable=True, resizable=True, floatingFilter=True)
    gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=page_size)
    gb.configure_grid_options(domLayout="normal", rowHeight=36, headerHeight=38)

    # Highlight search matches
    cell_renderer = JsCode(
        """
        function(params) {
          const q = (params.context && params.context.query) ? params.context.query.toLowerCase() : "";
          const v = (params.value === null || params.value === undefined) ? "" : params.value.toString();
          if (!q || !v.toLowerCase().includes(q)) return v;

          const i = v.toLowerCase().indexOf(q);
          const before = v.substring(0, i);
          const match = v.substring(i, i + q.length);
          const after = v.substring(i + q.length);

          const e = document.createElement('span');
          e.innerHTML = before +
                        '<span style="background:yellow;color:black;font-weight:600;border-radius:3px;padding:0 2px">' +
                        match +
                        '</span>' + after;
          return e;
        }
        """
    )
    highlight_cols = ["COMPANY_NAME", "BANK_NAME", "COMPANY_CATEGORY", "LOCATION", "STATE", "BANK", "PINCODE"]
    for c in [c for c in highlight_cols if c in df.columns]:
        gb.configure_column(c, cellRenderer=cell_renderer)

    grid_options = gb.build()
    grid_options["context"] = {"query": (search_query or "")}

    return AgGrid(
        df,
        gridOptions=grid_options,
        theme="streamlit",
        allow_unsafe_jscode=True,
        update_mode=GridUpdateMode.NO_UPDATE,
        fit_columns_on_grid_load=True,
        height=500,
    )


# ----------------------------
# --- Main App Logic ---
# ----------------------------
if check_password():

    # Tabs for navigation
    tab_company, tab_pincode, tab_dashboard, tab_history, tab_about = st.tabs(
        ["🏢 Company Search", "📮 Pincode Search", "📊 Dashboard", "🕘 History", "ℹ About"]
    )

    # --- Company Search ---
    with tab_company:
        st.title("☁🏦 Company Listing Search")
        data = load_company_data()

        colA, colB, colC = st.columns(3)
        colA.metric("Total Rows", f"{len(data):,}")
        colB.metric("Banks", data["BANK_NAME"].nunique() if "BANK_NAME" in data.columns else 0)
        colC.metric("Categories", data["COMPANY_CATEGORY"].nunique() if "COMPANY_CATEGORY" in data.columns else 0)

        with st.container(border=True):
            search_query = st.text_input("Search companies / banks / categories")
            bank_filter = st.selectbox("🏦 Quick filter: Bank", ["All"] + sorted(data["BANK_NAME"].dropna().unique().tolist()))
            category_filter = st.selectbox("📂 Quick filter: Category", ["All"] + sorted(data["COMPANY_CATEGORY"].dropna().unique().tolist()))

            if st.button("🔎 Search Companies"):
                results = data.copy()
                if search_query:
                    q = search_query.lower()
                    mask_parts = []
                    for col in ["COMPANY_NAME", "BANK_NAME", "COMPANY_CATEGORY"]:
                        if col in results.columns:
                            mask_parts.append(results[col].astype(str).str.lower().str.contains(q, regex=False))
                    if mask_parts:
                        mask = mask_parts[0]
                        for m in mask_parts[1:]:
                            mask |= m
                        results = results[mask]
                if bank_filter != "All":
                    results = results[results["BANK_NAME"] == bank_filter]
                if category_filter != "All":
                    results = results[results["COMPANY_CATEGORY"] == category_filter]

                st.success(f"✅ Found {len(results)} matching result(s)")
                render_grid(results, search_query, key="company")

                # History
                if "history" not in st.session_state:
                    st.session_state.history = []
                st.session_state.history.append({
                    "tab": "company",
                    "query": search_query,
                    "bank": bank_filter,
                    "category": category_filter,
                    "results": int(len(results)),
                    "time": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
                })
                st.session_state.history = st.session_state.history[-100:]

                if len(results) > 0:
                    csv = results.to_csv(index=False).encode("utf-8")
                    excel_buffer = io.BytesIO()
                    results.to_excel(excel_buffer, index=False, engine="openpyxl")
                    c1, c2 = st.columns(2)
                    c1.download_button("⬇ Download CSV", data=csv, file_name="company_results.csv", mime="text/csv")
                    c2.download_button("⬇ Download Excel", data=excel_buffer, file_name="company_results.xlsx",
                                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            else:
                st.info("ℹ Enter search term and click *Search Companies* to begin.")

    # --- Pincode Search ---
    with tab_pincode:
        st.title("📮🏦 Pincode Listing Search")
        data = load_pincode_data()

        with st.container(border=True):
            search_query = st.text_input("Enter Pincode / Location / State")
            bank_filter = st.selectbox("🏦 Quick filter: Bank", ["All"] + sorted(data["BANK"].dropna().unique().tolist()))
            state_filter = st.selectbox("🌍 Quick filter: State", ["All"] + sorted(data["STATE"].dropna().unique().tolist()))

            if st.button("🔎 Search Pincodes"):
                results = data.copy()
                if search_query:
                    q = search_query.lower()
                    mask = (
                        data["PINCODE"].astype(str).str.contains(q, regex=False, na=False)
                        | data["LOCATION"].str.lower().str.contains(q, regex=False, na=False)
                        | data["STATE"].str.lower().str.contains(q, regex=False, na=False)
                    )
                    results = results[mask]
                if bank_filter != "All":
                    results = results[results["BANK"] == bank_filter]
                if state_filter != "All":
                    results = results[results["STATE"] == state_filter]

                st.success(f"✅ Found {len(results)} matching result(s)")
                render_grid(results, search_query, key="pincode")

                # History
                if "history" not in st.session_state:
                    st.session_state.history = []
                st.session_state.history.append({
                    "tab": "pincode",
                    "query": search_query,
                    "bank": bank_filter,
                    "state": state_filter,
                    "results": int(len(results)),
                    "time": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
                })
                st.session_state.history = st.session_state.history[-100:]

                if len(results) > 0:
                    csv = results.to_csv(index=False).encode("utf-8")
                    excel_buffer = io.BytesIO()
                    results.to_excel(excel_buffer, index=False, engine="openpyxl")
                    c1, c2 = st.columns(2)
                    c1.download_button("⬇ Download CSV", data=csv, file_name="pincode_results.csv", mime="text/csv")
                    c2.download_button("⬇ Download Excel", data=excel_buffer, file_name="pincode_results.xlsx",
                                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            else:
                st.info("ℹ Enter search term and click *Search Pincodes* to begin.")

    # --- Dashboard ---
    with tab_dashboard:
        st.title("📊 Combined Dashboard")
        company_data = load_company_data()
        pincode_data = load_pincode_data()

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🏦 Companies by Bank")
            bank_counts = company_data["BANK_NAME"].value_counts()
            fig, ax = plt.subplots()
            bank_counts.plot(kind="bar", ax=ax, color="crimson")
            ax.set_ylabel("Number of Companies")
            ax.set_title("Companies per Bank")
            st.pyplot(fig)

        with col2:
            st.subheader("📂 Companies by Category")
            category_counts = company_data["COMPANY_CATEGORY"].value_counts()
            fig, ax = plt.subplots()
            category_counts.plot(kind="pie", autopct="%1.1f%%", ax=ax, colors=plt.cm.Set3.colors)
            ax.axis("equal")
            ax.set_ylabel("")
            ax.set_title("Company Category Share")
            st.pyplot(fig)

        st.markdown("<hr>", unsafe_allow_html=True)
        st.subheader("📮 Pincode Data Snapshot")
        st.dataframe(pincode_data.head(20))

    # --- History ---
    with tab_history:
        st.title("🕘 Search History (last 100)")
        if "history" not in st.session_state or len(st.session_state.history) == 0:
            st.info("No searches yet.")
        else:
            hist_df = pd.DataFrame(st.session_state.history)
            render_grid(hist_df, "", key="history")

    # --- About ---
    with tab_about:
        st.title("ℹ About this App")
        st.markdown(
            """
            This app is a *private listing search tool*.  

            🔑 Features:  
            - Secure login with password protection  
            - 🏢 Company Listing Checker (by Company / Bank / Category)  
            - 📮 Pincode Listing Checker (by Pincode / Location / State)  
            - 📊 Dashboard with charts and data snapshots  
            - 🕘 Search history (last 100 searches)  
            - ⬇ Download results as CSV/Excel  
            - Beautiful *dark neon UI styling*  

            💡 Built with *Streamlit + Pandas + Matplotlib + AgGrid*  
            """
        )
        st.markdown("<h4 style='text-align: center; color: #FFD700;'>✨ Developed by Nihil ✨</h4>", unsafe_allow_html=True)
