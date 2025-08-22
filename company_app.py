import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import io

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
    return True

# ----------------------------
# --- Custom CSS Styling ---
# ----------------------------
st.markdown(
    """
    <style>
    .stApp { background-color: #0d001a; }
    h1, h2, h3, h4 { color: #FFD700; text-align: center; font-family: 'Trebuchet MS', sans-serif; font-weight: bold; text-shadow: 0px 0px 10px #FF0000; }
    .highlight { background-color: yellow; font-weight: bold; }
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
# --- Search Helpers ---
# ----------------------------
def highlight_text(df, query):
    """Highlight search terms inside dataframe results"""
    if not query:
        return df
    query = query.lower()
    return df.style.applymap(lambda v: f"background-color: yellow; font-weight: bold;" 
                              if isinstance(v, str) and query in v.lower() else "")

def paginate_dataframe(df, page_size=50, key="page"):
    """Return a single page of dataframe"""
    total_pages = (len(df) - 1) // page_size + 1
    page = st.number_input("Page", 1, total_pages, 1, key=key)
    start = (page - 1) * page_size
    end = start + page_size
    return df.iloc[start:end], total_pages

# ----------------------------
# --- Main App Logic ---
# ----------------------------
if check_password():

    # Sidebar Navigation
    st.sidebar.title("📂 Navigation")
    menu = st.sidebar.radio(
        "Choose Feature",
        ["🏢 Company Listing Checker", "📮 Pincode Listing Checker", "📊 Dashboard", "📜 History", "ℹ About App"],
    )

    # Init search history
    if "history" not in st.session_state:
        st.session_state.history = []

    # ----------------------------
    # --- Company Listing Checker ---
    # ----------------------------
    if menu == "🏢 Company Listing Checker":
        st.title("☁🏦 Company Listing Search")
        data = load_company_data()

        search_query = st.text_input("Enter search term")
        bank_filter = st.selectbox("🏦 Filter by Bank (optional)", ["All"] + sorted(data["BANK_NAME"].dropna().unique().tolist()))
        category_filter = st.selectbox("📂 Filter by Category (optional)", ["All"] + sorted(data["COMPANY_CATEGORY"].dropna().unique().tolist()))

        if st.button("🔎 Search Companies"):
            results = data.copy()

            if search_query:
                q = search_query.lower()
                mask = (
                    data["COMPANY_NAME"].str.lower().str.contains(q, regex=False, na=False)
                    | data["BANK_NAME"].str.lower().str.contains(q, regex=False, na=False)
                    | data["COMPANY_CATEGORY"].str.lower().str.contains(q, regex=False, na=False)
                )
                results = results[mask]

            if bank_filter != "All":
                results = results[results["BANK_NAME"] == bank_filter]
            if category_filter != "All":
                results = results[results["COMPANY_CATEGORY"] == category_filter]

            total = len(results)
            st.success(f"✅ Found {total} matching result(s)")

            if total > 0:
                # Save to history
                st.session_state.history.append(("Company Search", search_query, total))
                st.session_state.history = st.session_state.history[-100:]  # keep last 100

                page_size = st.slider("Rows per page", 20, 200, 50)
                page_df, total_pages = paginate_dataframe(results, page_size, key="comp_page")

                st.dataframe(page_df)

                # Downloads
                csv = results.to_csv(index=False).encode("utf-8")
                excel_buffer = io.BytesIO()
                results.to_excel(excel_buffer, index=False, engine="openpyxl")
                st.download_button("⬇ Download Results (CSV)", data=csv, file_name="company_results.csv", mime="text/csv")
                st.download_button("⬇ Download Results (Excel)", data=excel_buffer, file_name="company_results.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # ----------------------------
    # --- Pincode Listing Checker ---
    # ----------------------------
    elif menu == "📮 Pincode Listing Checker":
        st.title("📮🏦 Pincode Listing Search")
        data = load_pincode_data()

        search_query = st.text_input("Enter Pincode / Location / State")
        bank_filter = st.selectbox("🏦 Filter by Bank (optional)", ["All"] + sorted(data["BANK"].dropna().unique().tolist()))
        state_filter = st.selectbox("🌍 Filter by State (optional)", ["All"] + sorted(data["STATE"].dropna().unique().tolist()))

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

            total = len(results)
            st.success(f"✅ Found {total} matching result(s)")

            if total > 0:
                # Save to history
                st.session_state.history.append(("Pincode Search", search_query, total))
                st.session_state.history = st.session_state.history[-100:]

                page_size = st.slider("Rows per page", 20, 200, 50, key="rows2")
                page_df, total_pages = paginate_dataframe(results, page_size, key="pin_page")

                st.dataframe(page_df)

                # Downloads
                csv = results.to_csv(index=False).encode("utf-8")
                excel_buffer = io.BytesIO()
                results.to_excel(excel_buffer, index=False, engine="openpyxl")
                st.download_button("⬇ Download Results (CSV)", data=csv, file_name="pincode_results.csv", mime="text/csv")
                st.download_button("⬇ Download Results (Excel)", data=excel_buffer, file_name="pincode_results.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # ----------------------------
    # --- Dashboard ---
    # ----------------------------
    elif menu == "📊 Dashboard":
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

    # ----------------------------
    # --- History Tab ---
    # ----------------------------
    elif menu == "📜 History":
        st.title("📜 Search History (Last 100)")
        if len(st.session_state.history) == 0:
            st.info("No searches yet.")
        else:
            hist_df = pd.DataFrame(st.session_state.history, columns=["Type", "Query", "Results"])
            st.dataframe(hist_df)

    # ----------------------------
    # --- About App ---
    # ----------------------------
    elif menu == "ℹ About App":
        st.title("ℹ About this App")
        st.markdown(
            """
            This app is a *private listing search tool*. 🔑 Features:
            - Secure login with password protection
            - 🏢 Company Listing Checker (by Company / Bank / Category)
            - 📮 Pincode Listing Checker (by Pincode / Location / State)
            - 📊 Dashboard with charts and data snapshots
            - ⬇ Download results as CSV/Excel
            - 📜 Search history (last 100)
            - Beautiful *dark neon UI styling*
            
            💡 Built with *Streamlit + Pandas + Matplotlib*
            """
        )
        st.markdown("<h4 style='text-align: center; color: #FFD700;'>✨ Developed by Nihil ✨</h4>", unsafe_allow_html=True)
