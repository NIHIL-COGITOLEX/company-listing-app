import streamlit as st
import pandas as pd

# --- 🔐 PASSWORD PROTECTION ---
PASSWORD = "NIHIL IS GREAT"  # <-- CHANGE THIS to whatever password you want

st.set_page_config(page_title="Private Company Listing App", layout="wide")
st.markdown("<h2 style='text-align: center;'>🔐 Protected App</h2>", unsafe_allow_html=True)

password_input = st.text_input("Enter Password", type="password")

if password_input != PASSWORD:
    st.warning("Please enter the correct password to continue.")
    st.stop()  # ⛔️ Stops the app until correct password is entered
    
import streamlit as st
import pandas as pd

# --- Page Config ---
st.set_page_config(page_title="Company Listing Search", page_icon="☁️", layout="wide")

# --- Custom CSS Styling ---
st.markdown(
    """
    <style>
        /* Premium purple background */
        .stApp {
            background-color: #1a001f; /* deep premium purple */
        }

        /* App container border: thin red + golden double line */
        .stApp::before {
            content: "";
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            border: 2px double #FFD700; /* golden */
            outline: 1px solid #FF0000; /* premium thin red */
            pointer-events: none;
            z-index: 9999;
        }

        /* Title */
        h1 {
            color: #FFD700; /* gold */
            text-align: center;
            font-family: 'Trebuchet MS', sans-serif;
            font-weight: bold;
            text-shadow: 0px 0px 8px #ff0000;
        }

        /* Search box (Glassmorphism style) */
        .stTextInput > div > div > input {
            background: rgba(255, 255, 255, 0.15);
            border: 1px solid rgba(255, 0, 0, 0.6);
            border-radius: 14px;
            backdrop-filter: blur(15px) saturate(180%);
            -webkit-backdrop-filter: blur(15px) saturate(180%);
            color: #ffffff;
            font-size: 16px;
            padding: 12px;
            box-shadow: 0px 4px 20px rgba(0, 0, 0, 0.5);
        }

        .stTextInput > div > div > input::placeholder {
            color: #FFD700;
            font-style: italic;
        }

        /* Dataframe (Glassmorphism style) */
        .stDataFrame, .stDataFrame > div {
            background: rgba(255, 255, 255, 0.12) !important;
            border-radius: 14px !important;
            backdrop-filter: blur(12px) saturate(180%) !important;
            -webkit-backdrop-filter: blur(12px) saturate(180%) !important;
            border: 1px solid rgba(255, 0, 0, 0.6) !important;
            box-shadow: 0px 4px 20px rgba(0, 0, 0, 0.6) !important;
        }

        /* Success / Info / Error */
        .stSuccess {
            background-color: rgba(0, 255, 128, 0.15);
            color: #00ffcc;
            font-weight: bold;
            border-radius: 10px;
        }
        .stInfo {
            background-color: rgba(0, 128, 255, 0.15);
            color: #66b3ff;
            font-weight: bold;
            border-radius: 10px;
        }
        .stError {
            background-color: rgba(255, 0, 0, 0.2);
            color: #ff6666;
            font-weight: bold;
            border-radius: 10px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Load Data ---
@st.cache_data
def load_data(file):
    df = pd.read_excel(file)
    # Clean column names
    df.columns = [c.strip().upper().replace(" ", "_") for c in df.columns]
    return df

# --- App Title ---
st.title("☁️🏦 Company Listing Search App")

# File upload
uploaded_file = st.file_uploader("Upload your Company Listing Excel", type=["xlsx"])

if uploaded_file:
    data = load_data(uploaded_file)

    # Search box (with placeholder)
    search_query = st.text_input("", placeholder="Search your company here...")

    if search_query:
        results = data[data["COMPANY_NAME"].str.contains(search_query, case=False, na=False)]

        if not results.empty:
            st.success(f"✅ Found {len(results)} matching result(s)")
            st.dataframe(results[["COMPANY_NAME", "BANK_NAME", "COMPANY_CATEGORY"]])
        else:
            st.error("❌ No matches found.")
else:
    st.info("☁️ Please upload your Excel file to begin.")

# --- Custom Message ---
st.markdown(
    "<h3 style='text-align: center; color: #FFD700;'>💡 Ask Nihil!</h3>",
    unsafe_allow_html=True,
)

