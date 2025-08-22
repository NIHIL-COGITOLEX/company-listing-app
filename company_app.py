import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import io

# --- Password Protection ---
PASSWORD = "NIHIL IS GREAT"  # 🔑 Change this if needed
st.set_page_config(page_title="Private Listing App", page_icon="☁", layout="wide")


def check_password():
    """Password protection with session state"""
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


# --- Custom CSS ---
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


# --- Load Company Data ---
@st.cache_data
def load_company_data():
    df = pd.read_excel("company_listings.xlsx.xlsx")  # ✅ double extension
    df.columns = [c.strip().upper().replace(" ", "_") for c in df.columns]
    return df


# --- Load Pincode Data ---
@st.cache_data
def load_pincode_data():
    df = pd.read_excel("pincode_listings.xlsx.xlsx")  # ✅ also double extension
    df.columns = [c.strip().upper().replace(" ", "_") for c in df.columns]
    return df


# --- Check Password ---
if check_password():

    # Sidebar Navigation
    st.sidebar.title("📂 Navigation")
    menu = st.sidebar.radio(
        "Go to",
        ["🔎 Search Companies", "📍 Search Pincodes", "📊 Dashboards", "ℹ About App"]
    )

    # Load Data
    company_data = load_company_data()
    pincode_data = load_pincode_data()

    # --- COMPANY SEARCH ---
    if menu == "🔎 Search Companies":
        st.title("☁🏦 Company Listing Search")

        search_query = st.text_input("Enter search term")
        bank_filter = st.selectbox("🏦 Filter by Bank (optional)", ["All"] + sorted(company_data["BANK_NAME"].dropna().unique().tolist()))
        category_filter = st.selectbox("📂 Filter by Category (optional)", ["All"] + sorted(company_data["COMPANY_CATEGORY"].dropna().unique().tolist()))

        if st.button("🔎 Search Companies"):
            results = company_data.copy()

            if search_query:
                query = search_query.lower()
                mask = (
                    results["COMPANY_NAME"].str.lower().str.contains(query, regex=False, na=False)
                    | results["BANK_NAME"].str.lower().str.contains(query, regex=False, na=False)
                    | results["COMPANY_CATEGORY"].str.lower().str.contains(query, regex=False, na=False)
                )
                results = results[mask]

            if bank_filter != "All":
                results = results[results["BANK_NAME"] == bank_filter]

            if category_filter != "All":
                results = results[results["COMPANY_CATEGORY"] == category_filter]

            total = len(results)
            st.success(f"✅ Found {total} company result(s)")

            st.dataframe(results.head(500))

            if total > 0:
                csv = results.to_csv(index=False).encode("utf-8")
                excel_buffer = io.BytesIO()
                results.to_excel(excel_buffer, index=False, engine="openpyxl")
                st.download_button("⬇ Download Company Results (CSV)", data=csv, file_name="company_results.csv", mime="text/csv")
                st.download_button("⬇ Download Company Results (Excel)", data=excel_buffer, file_name="company_results.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # --- PINCODE SEARCH ---
    elif menu == "📍 Search Pincodes":
        st.title("📍 Pincode Listing Search")

        search_query = st.text_input("Enter Pincode, Bank, or Location")
        bank_filter = st.selectbox("🏦 Filter by Bank (optional)", ["All"] + sorted(pincode_data["BANK"].dropna().unique().tolist()))
        state_filter = st.selectbox("🌍 Filter by State (optional)", ["All"] + sorted(pincode_data["STATE"].dropna().unique().tolist()))

        if st.button("🔎 Search Pincodes"):
            results = pincode_data.copy()

            if search_query:
                query = search_query.lower()
                mask = (
                    results["PINCODE"].astype(str).str.contains(query, regex=False, na=False)
                    | results["BANK"].str.lower().str.contains(query, regex=False, na=False)
                    | results["LOCATION"].str.lower().str.contains(query, regex=False, na=False)
                    | results["STATE"].str.lower().str.contains(query, regex=False, na=False)
                )
                results = results[mask]

            if bank_filter != "All":
                results = results[results["BANK"] == bank_filter]

            if state_filter != "All":
                results = results[results["STATE"] == state_filter]

            total = len(results)
            st.success(f"✅ Found {total} pincode result(s)")

            st.dataframe(results.head(500))

            if total > 0:
                csv = results.to_csv(index=False).encode("utf-8")
                excel_buffer = io.BytesIO()
                results.to_excel(excel_buffer, index=False, engine="openpyxl")
                st.download_button("⬇ Download Pincode Results (CSV)", data=csv, file_name="pincode_results.csv", mime="text/csv")
                st.download_button("⬇ Download Pincode Results (Excel)", data=excel_buffer, file_name="pincode_results.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # --- DASHBOARDS ---
    elif menu == "📊 Dashboards":
        st.title("📊 Data Dashboards")

        st.subheader("🏦 Companies by Bank")
        bank_counts = company_data["BANK_NAME"].value_counts()
        fig, ax = plt.subplots()
        bank_counts.plot(kind="bar", ax=ax, color="crimson")
        ax.set_ylabel("Number of Companies")
        ax.set_title("Companies per Bank")
        st.pyplot(fig)

        st.subheader("📂 Companies by Category")
        category_counts = company_data["COMPANY_CATEGORY"].value_counts()
        fig, ax = plt.subplots()
        category_counts.plot(kind="pie", autopct="%1.1f%%", ax=ax, colors=plt.cm.Set3.colors)
        ax.set_ylabel("")
        ax.set_title("Company Category Share")
        st.pyplot(fig)

        st.markdown("<hr>", unsafe_allow_html=True)
        st.subheader("📍 Pincode Data Snapshot")
        st.dataframe(pincode_data.head(20))

    # --- ABOUT PAGE ---
    elif menu == "ℹ About App":
        st.title("ℹ About this App")
        st.markdown(
            """
            This app is a *private listing tool* with:  

            🔑 Features:  
            - Secure login with password protection  
            - Company search by *Name, Bank, Category*  
            - Pincode search by *Pincode, Bank, Location, State*  
            - 📊 Dashboards with interactive summary charts  
            - ⬇ Download results as *CSV/Excel*  
            - Beautiful *dark neon UI styling*  

            💡 Built with *Streamlit + Pandas + Matplotlib*  
            """
        )
        st.markdown("<h4 style='text-align: center; color: #FFD700;'>✨ Developed by Nihil ✨</h4>", unsafe_allow_html=True)
