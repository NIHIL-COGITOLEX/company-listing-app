import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# --- 🔐 PASSWORD PROTECTION ---
PASSWORD = "NIHIL IS GREAT"  # <-- Change this if needed

st.set_page_config(page_title="Private Company Listing App", page_icon="☁️", layout="wide")

st.markdown("<h2 style='text-align: center;'>🔐 Protected App</h2>", unsafe_allow_html=True)
password_input = st.text_input("Enter Password", type="password")

if password_input != PASSWORD:
    st.warning("Please enter the correct password to continue.")
    st.stop()


# --- Custom CSS Styling ---
st.markdown(
    """
    <style>
        .stApp { background-color: #1a001f; }
        .stApp::before {
            content: ""; position: fixed; top: 0; left: 0; right: 0; bottom: 0;
            border: 2px double #FFD700; outline: 1px solid #FF0000;
            pointer-events: none; z-index: 9999;
        }
        h1, h2, h3 {
            color: #FFD700; text-align: center;
            font-family: 'Trebuchet MS', sans-serif; font-weight: bold;
            text-shadow: 0px 0px 8px #ff0000;
        }
        .stTextInput > div > div > input {
            background: rgba(255, 255, 255, 0.15);
            border: 1px solid rgba(255, 0, 0, 0.6);
            border-radius: 14px; backdrop-filter: blur(15px) saturate(180%);
            color: #ffffff; font-size: 16px; padding: 12px;
            box-shadow: 0px 4px 20px rgba(0, 0, 0, 0.5);
        }
        .stTextInput > div > div > input::placeholder {
            color: #FFD700; font-style: italic;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# --- Load Data ---
@st.cache_data
def load_data():
    df = pd.read_excel("data/company_listings.xlsx")
    df.columns = [c.strip().upper().replace(" ", "_") for c in df.columns]
    return df


# --- Sidebar Navigation ---
st.sidebar.title("📂 Navigation")
menu = st.sidebar.radio("Go to", ["🔎 Search Companies", "📊 Summary Dashboard", "ℹ️ About App"])


# --- Load Data Once ---
data = load_data()


# --- Search Page ---
if menu == "🔎 Search Companies":
    st.title("☁️🏦 Company Listing Search App")

    search_query = st.text_input("", placeholder="Search by Company, Bank, or Category...")

    if search_query:
        mask = (
            data["COMPANY_NAME"].str.contains(search_query, case=False, na=False)
            | data["BANK_NAME"].str.contains(search_query, case=False, na=False)
            | data["COMPANY_CATEGORY"].str.contains(search_query, case=False, na=False)
        )
        results = data[mask]

        if not results.empty:
            st.success(f"✅ Found {len(results)} matching result(s)")
            st.dataframe(results[["COMPANY_NAME", "BANK_NAME", "COMPANY_CATEGORY"]])

            # --- Download Results ---
            st.download_button(
                "⬇️ Download results as Excel",
                data=results.to_csv(index=False).encode("utf-8"),
                file_name="search_results.csv",
                mime="text/csv",
            )
        else:
            st.error("❌ No matches found.")
    else:
        st.info("☁️ Please enter a company name, bank, or category to search.")


# --- Dashboard Page ---
elif menu == "📊 Summary Dashboard":
    st.title("📊 Company Data Dashboard")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🏦 Companies by Bank")
        bank_counts = data["BANK_NAME"].value_counts()
        fig, ax = plt.subplots()
        bank_counts.plot(kind="bar", ax=ax)
        ax.set_ylabel("Number of Companies")
        st.pyplot(fig)

    with col2:
        st.subheader("📂 Companies by Category")
        category_counts = data["COMPANY_CATEGORY"].value_counts()
        fig, ax = plt.subplots()
        category_counts.plot(kind="pie", autopct="%1.1f%%", ax=ax)
        ax.set_ylabel("")
        st.pyplot(fig)

    st.markdown("<hr>", unsafe_allow_html=True)
    st.subheader("📈 Data Snapshot")
    st.dataframe(data.head(20))


# --- About Page ---
elif menu == "ℹ️ About App":
    st.title("ℹ️ About this App")
    st.markdown(
        """
        This app is a **private company listing search tool**.  
        🔑 Features:  
        - Secure login with password protection  
        - Search by **Company, Bank, or Category**  
        - 📊 Dashboard with summary charts  
        - ⬇️ Downloadable search results  
        - Beautiful UI with custom styling  

        💡 Built with **Streamlit + Pandas + Matplotlib**  
        """
    )

    st.markdown("<h3 style='text-align: center; color: #FFD700;'>💡 Ask Nihil!</h3>", unsafe_allow_html=True)
