# company_app.py

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import io
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

# ----------------------------
# --- App Configuration ---
# ----------------------------
st.set_page_config(page_title="Private Listing App", page_icon="☁", layout="wide")
PASSWORD = "NIHIL IS GREAT"  # 🔑 Change this if you want

# ----------------------------
# --- Password Protection ---
# ----------------------------
def check_password():
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
        .stSidebar { background: #1a001f; }
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
# --- Helper: AgGrid Display ---
# ----------------------------
def show_aggrid(df):
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=20)
    gb.configure_side_bar()
    gb.configure_default_column(filter=True, sortable=True, resizable=True)
    gb.configure_selection("multiple", use_checkbox=True)
    gridOptions = gb.build()

    grid_response = AgGrid(
        df,
        gridOptions=gridOptions,
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        enable_enterprise_modules=False,
        fit_columns_on_grid_load=True,
        height=400,
        theme="alpine",
    )
    return grid_response

# ----------------------------
# --- Main App Logic ---
# ----------------------------
if check_password():

    # Sidebar Navigation
    st.sidebar.title("📂 Navigation")
    menu = st.sidebar.radio(
        "Choose Feature",
        ["🏢 Company Listing Checker", "📮 Pincode Listing Checker", "📊 Dashboard", "🕑 History", "ℹ About App"]
    )

    if st.sidebar.button("🔒 Logout"):
        st.session_state.password_correct = False
        st.experimental_rerun()

    # Company Listing Checker
    if menu == "🏢 Company Listing Checker":
        st.title("☁🏦 Company Listing Search")
        data = load_company_data()
        search_query = st.text_input("Enter search term")

        if st.button("🔎 Search Companies"):
            results = data.copy()
            if search_query:
                mask = (
                    data["COMPANY_NAME"].str.contains(search_query, case=False, na=False)
                    | data["BANK_NAME"].str.contains(search_query, case=False, na=False)
                    | data["COMPANY_CATEGORY"].str.contains(search_query, case=False, na=False)
                )
                results = results[mask]

            st.success(f"✅ Found {len(results)} matching result(s)")
            show_aggrid(results)

            # Save to history
            if "history" not in st.session_state:
                st.session_state.history = []
            st.session_state.history.append(("Company Search", search_query, len(results)))
            if len(st.session_state.history) > 100:
                st.session_state.history = st.session_state.history[-100:]

    # Pincode Listing Checker
    elif menu == "📮 Pincode Listing Checker":
        st.title("📮🏦 Pincode Listing Search")
        data = load_pincode_data()
        search_query = st.text_input("Enter Pincode / Location / State")

        if st.button("🔎 Search Pincodes"):
            results = data.copy()
            if search_query:
                mask = (
                    data["PINCODE"].astype(str).str.contains(search_query, case=False, na=False)
                    | data["LOCATION"].str.contains(search_query, case=False, na=False)
                    | data["STATE"].str.contains(search_query, case=False, na=False)
                )
                results = results[mask]

            st.success(f"✅ Found {len(results)} matching result(s)")
            show_aggrid(results)

            # Save to history
            if "history" not in st.session_state:
                st.session_state.history = []
            st.session_state.history.append(("Pincode Search", search_query, len(results)))
            if len(st.session_state.history) > 100:
                st.session_state.history = st.session_state.history[-100:]

    # Dashboard
    elif menu == "📊 Dashboard":
        st.title("📊 Combined Dashboard")
        company_data = load_company_data()
        pincode_data = load_pincode_data()

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🏦 Companies by Bank")
            fig, ax = plt.subplots()
            company_data["BANK_NAME"].value_counts().plot(kind="bar", ax=ax, color="crimson")
            st.pyplot(fig)

        with col2:
            st.subheader("📂 Companies by Category")
            fig, ax = plt.subplots()
            company_data["COMPANY_CATEGORY"].value_counts().plot(kind="pie", autopct="%1.1f%%", ax=ax)
            ax.axis("equal")
            st.pyplot(fig)

        st.subheader("📮 Pincode Data Snapshot")
        st.dataframe(pincode_data.head(20))

    # History Tab
    elif menu == "🕑 History":
        st.title("🕑 Search History (Last 100)")
        if "history" in st.session_state and st.session_state.history:
            hist_df = pd.DataFrame(st.session_state.history, columns=["Type", "Query", "Results"])
            show_aggrid(hist_df)
        else:
            st.info("No history yet.")

    # About App
    elif menu == "ℹ About App":
        st.title("ℹ About this App")
        st.markdown("This app is a *private listing search tool* with AgGrid and history tracking.")
