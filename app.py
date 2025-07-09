import streamlit as st
import os
import requests
from dotenv import load_dotenv
import pandas as pd
import re
from PIL import Image
import csv
import hashlib

# --- Load API key ---
load_dotenv()
API_KEY = os.getenv("OPENROUTER_API_KEY")
USER_FILE = "users.csv"

# --- Page config ---
st.set_page_config(page_title="Data Analyst AI Assistant (UAT)", page_icon="📊", layout="wide")

# --- Dark Mode Toggle ---
dark_mode = st.sidebar.toggle("🌙 Dark Mode")

# --- Custom CSS Styling ---
light_css = """
<style>
.fixed-bottom-form {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background-color: white;
    padding: 1rem;
    box-shadow: 0 -1px 5px rgba(0,0,0,0.1);
    z-index: 1000;
}
</style>
"""

dark_css = """
<style>
.fixed-bottom-form {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background-color: #1a1a1a;
    padding: 1rem;
    box-shadow: 0 -1px 5px rgba(255,255,255,0.1);
    z-index: 1000;
}
</style>
"""

st.markdown(dark_css if dark_mode else light_css, unsafe_allow_html=True)

# --- Header ---
st.markdown("""
<h2>📊 AI-Powered Data Analyst Assistant (UAT)</h2>
<p>Get instant help with Excel formulas, SQL queries, dashboards, Python Queries, automation, and data cleaning.</p>
""", unsafe_allow_html=True)

# --- Helpers for hashing passwords ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# --- Load or Initialize Users from CSV ---
def load_users():
    if not os.path.exists(USER_FILE):
        with open(USER_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["email", "password"])
    users = {}
    with open(USER_FILE, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            users[row["email"]] = row["password"]
    return users

def save_user(email, password):
    hashed = hash_password(password)
    with open(USER_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([email, hashed])

# --- Sign Up and Login ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "users" not in st.session_state:
    st.session_state.users = load_users()

if not st.session_state.authenticated:
    st.markdown("### 🔐 Sign In or Sign Up")
    option = st.radio("Choose an option:", ["Login", "Sign Up"], horizontal=True)

    email = st.text_input("📧 Email")
    password = st.text_input("🔒 Password", type="password")

    if option == "Sign Up":
        if st.button("Create Account"):
            if email and password:
                if email in st.session_state.users:
                    st.warning("🚫 Email already registered. Try logging in.")
                else:
                    save_user(email, password)
                    st.session_state.users[email] = hash_password(password)
                    st.success("✅ Account created. You can now log in.")
            else:
                st.error("Please provide both email and password.")
        st.stop()
    else:  # Login
if st.button("Login"):
    if valid_credentials:
        st.session_state.authenticated = True
        if not st.session_state.get("has_rerun", False):
            st.session_state.has_rerun = True
            st.experimental_rerun()
    else:
        st.error("Invalid credentials. Please try again.")
        st.stop()

if st.sidebar.button("🚪 Logout"):
    st.session_state.authenticated = False
    st.experimental_rerun()

# --- Initialize Chat History ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# --- Show latest Q&A ---
if st.session_state.chat_history:
    latest_q, latest_a = st.session_state.chat_history[-1]
    st.markdown("### 🧠 Latest Response")
    st.markdown(f"**You:** {latest_q}")
    st.code(latest_a)
    st.markdown(f"""
        <button onclick=\"navigator.clipboard.writeText(`{latest_a}`)\" style=\"
            background-color:#4CAF50;
            color:white;
            border:none;
            padding:8px 16px;
            margin-top:10px;
            border-radius:5px;
            cursor:pointer;\">
            📋 Copy to Clipboard
        </button>
    """, unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.button("👍 Helpful", key="feedback_yes")
    with col2:
        st.button("👎 Not Helpful", key="feedback_no")

# --- Chat Input Form ---
st.markdown("<div class='fixed-bottom-form'>", unsafe_allow_html=True)
with st.form(key="chat_form"):
    user_input = st.text_area("📥 Type your question here:", placeholder="Press ALT+Enter for new line. Press Enter to send.")
    submit = st.form_submit_button("🚀 Ask")

if submit and user_input:
    cleaned_input = user_input.lower().strip()

    if cleaned_input in ["hi", "hello", "hey", "yo", "yoo", "hola", "hii", "hiii", "hey there"]:
        st.info("👋 Hello! Please ask something related to Excel, SQL, or data analysis.")
    else:
        with st.spinner("Thinking..."):
            headers = {
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            }
            body = {
                "model": "mistralai/mistral-7b-instruct",
                "messages": [
                    {"role": "system", "content": "You are a helpful AI assistant focused on data analysis, Excel, SQL, and automation."},
                    {"role": "user", "content": user_input}
                ]
            }
            response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=body)
            if response.status_code == 200:
                answer = response.json()["choices"][0]["message"]["content"]
                answer = re.sub(r'https?://\\S+', '[link removed]', answer)
                st.session_state.chat_history.append((user_input, answer))
                st.experimental_rerun()
            else:
                st.error(f"Error {response.status_code}: {response.text}")
st.markdown("</div>", unsafe_allow_html=True)

# --- Sidebar: Search and Chat History ---
with st.sidebar:
    selected_tab = st.radio("📂 View", ["Search History", "Chat History"])
    if selected_tab == "Search History":
        st.markdown("### 🔍 Search History")
        for i, (q, _) in enumerate(reversed(st.session_state.chat_history), 1):
            st.markdown(f"- {q}")
    if selected_tab == "Chat History":
        st.markdown("### 🧠 Full Chat History")
        for i, (q, a) in enumerate(reversed(st.session_state.chat_history), 1):
            st.markdown(f"**Q{i}:** {q}")
            st.code(a)
            st.markdown("---")
    if st.button("🗑️ Clear History"):
        st.session_state.chat_history = []

    if not st.session_state.get("has_rerun", False):
    	st.session_state.has_rerun = True
    	st.experimental_rerun()
    
    if st.button("⬇️ Export to CSV"):
        df = pd.DataFrame(st.session_state.chat_history, columns=["Question", "Answer"])
        df.to_csv("chat_history.csv", index=False)
        st.success("Exported chat_history.csv")

# --- Footer ---
st.markdown("---")
st.caption("✅ Developed by the G 😎")
