import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import io

# --- Password Protection ---
PASSWORD = "NIHIL IS GREAT"  # 🔑 Change this if needed
st.set_page_config(page_title="Private Company Listing App", page_icon="☁️", layout="wide")

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


# --- Load Data ---
@st.cache_data
def load_data():
    df = pd.read_excel("company_listings.xlsx.xlsx")
    df.columns = [c.strip().upper().replace(" ", "_") for c in df.columns]
    return df


# --- Check Password ---
if check_password():

    # Sidebar Navigation
    st.sidebar.title("📂 Navigation")
    menu = st.sidebar.radio("Go to", ["🔎 Search Companies", "📊 Summary Dashboard", "📥 Upload Data", "ℹ️ About App"])

    # Load Data
    data = load_data()

    # --- SEARCH PAGE ---
    if menu == "🔎 Search Companies":
        st.title("☁️🏦 Company Listing Search App")

        search_query = st.text_input("", placeholder="Search by Company, Bank, or Category...")
        bank_filter = st.selectbox("🏦 Filter by Bank (optional)", ["All"] + sorted(data["BANK_NAME"].dropna().unique().tolist()))
        category_filter = st.selectbox("📂 Filter by Category (optional)", ["All"] + sorted(data["COMPANY_CATEGORY"].dropna().unique().tolist()))

        results = data.copy()

        # Apply Filters
        if search_query:
            mask = (
                results["COMPANY_NAME"].str.contains(search_query, case=False, na=False)
                | results["BANK_NAME"].str.contains(search_query, case=False, na=False)
                | results["COMPANY_CATEGORY"].str.contains(search_query, case=False, na=False)
            )
            results = results[mask]

        if bank_filter != "All":
            results = results[results["BANK_NAME"] == bank_filter]

        if category_filter != "All":
            results = results[results["COMPANY_CATEGORY"] == category_filter]

        if not results.empty:
            st.success(f"✅ Found {len(results)} matching result(s)")
            st.dataframe(results)

            # --- Download Results ---
            csv = results.to_csv(index=False).encode("utf-8")
            excel_buffer = io.BytesIO()
            results.to_excel(excel_buffer, index=False, engine="openpyxl")
            st.download_button("⬇️ Download CSV", data=csv, file_name="results.csv", mime="text/csv")
            st.download_button("⬇️ Download Excel", data=excel_buffer, file_name="results.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            st.warning("⚠️ No results found.")

    # --- DASHBOARD PAGE ---
    elif menu == "📊 Summary Dashboard":
        st.title("📊 Company Data Dashboard")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("🏦 Companies by Bank")
            bank_counts = data["BANK_NAME"].value_counts()
            fig, ax = plt.subplots()
            bank_counts.plot(kind="bar", ax=ax, color="crimson")
            ax.set_ylabel("Number of Companies")
            ax.set_title("Companies per Bank")
            st.pyplot(fig)

        with col2:
            st.subheader("📂 Companies by Category")
            category_counts = data["COMPANY_CATEGORY"].value_counts()
            fig, ax = plt.subplots()
            category_counts.plot(kind="pie", autopct="%1.1f%%", ax=ax, colors=plt.cm.Set3.colors)
            ax.set_ylabel("")
            ax.set_title("Company Category Share")
            st.pyplot(fig)

        st.markdown("<hr>", unsafe_allow_html=True)
        st.subheader("📈 Data Snapshot")
        st.dataframe(data.head(20))

    # --- UPLOAD PAGE ---
    elif menu == "📥 Upload Data":
        st.title("📥 Upload a New Dataset")
        uploaded_file = st.file_uploader("Upload Excel file", type=["xlsx"])
        if uploaded_file:
            new_data = pd.read_excel(uploaded_file)
            st.session_state["uploaded_data"] = new_data
            st.success("✅ File uploaded successfully! Reload to use new dataset.")
            st.dataframe(new_data.head())

    # --- ABOUT PAGE ---
    elif menu == "ℹ️ About App":
        st.title("ℹ️ About this App")
        st.markdown(
            """
            This app is a **private company listing search tool**.  

            🔑 Features:  
            - Secure login with password protection  
            - Search by **Company, Bank, or Category**  
            - 📊 Dashboard with interactive summary charts  
            - ⬇️ Download results as **CSV/Excel**  
            - 📥 Upload your own dataset  
            - Beautiful **dark neon UI styling**  

            💡 Built with **Streamlit + Pandas + Matplotlib**  
            """
        )
        st.markdown("<h4 style='text-align: center; color: #FFD700;'>✨ Developed by Nihil ✨</h4>", unsafe_allow_html=True)
