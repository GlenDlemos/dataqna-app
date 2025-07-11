import streamlit as st
import os
import requests
import pandas as pd
import re
import csv
import hashlib
from PIL import Image
from google.oauth2.service_account import Credentials
import gspread
from datetime import datetime
import pytz


# --- API Key and Google Sheet Setup ---
API_KEY = st.secrets["OPENROUTER_API_KEY"]
GOOGLE_SHEET_ID = st.secrets["GOOGLE_SHEET_ID"]

# Setup Google Sheets access
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_info(
    st.secrets["GOOGLE_SERVICE_ACCOUNT"], scopes=SCOPES
)
client = gspread.authorize(creds)
sheet = client.open_by_key(GOOGLE_SHEET_ID).sheet1

# --- Page config ---
st.set_page_config(page_title="Data Analyst AI Assistant (UAT)", page_icon="📊", layout="wide")

# --- Header ---
st.markdown("""
<h2>📊 AI-Powered Data Analyst Assistant (UAT)</h2>
<p>Get instant help with Excel formulas, SQL queries, dashboards, Python Queries, automation, and data cleaning.</p>
<a href="https://github.com/glendlemos/dataqna-app" target="_blank">🔗 View Source / Fork on GitHub</a><br>
<a href="https://share.streamlit.io/" target="_blank">✏️ Edit this App</a>
""", unsafe_allow_html=True)

# --- Password Hashing ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# --- Saving Chats to google Sheets ---
def log_chat_to_sheet(email, question, answer):
    try:
        ist = pytz.timezone("Asia/Kolkata")
        timestamp = datetime.now(ist).strftime("%Y-%m-%d %H:%M:%S")
        logs_sheet = client.open_by_key(GOOGLE_SHEET_ID).worksheet("chat_logs")
        logs_sheet.append_row([email, timestamp, question, answer])
    except Exception as e:
        st.warning(f"⚠️ Chat logging failed: {e}")

# --- Saving Feedback into google sheet ---

def log_feedback(email, question, feedback):
    try:
        ist = pytz.timezone("Asia/Kolkata")
        timestamp = datetime.now(ist).strftime("%Y-%m-%d %H:%M:%S")
        feedback_sheet = client.open_by_key(GOOGLE_SHEET_ID).worksheet("feedback_logs")
        feedback_sheet.append_row([email, timestamp, question, feedback])
    except Exception as e:
        st.warning(f"⚠️ Feedback logging failed: {e}")

# --- keeping the chat history after logout ---

def save_user_chat_history(email, chat_history):
    try:
        sheet_hist = client.open_by_key(GOOGLE_SHEET_ID).worksheet("chat_history_store")
        ist = pytz.timezone("Asia/Kolkata")
        for q, a in chat_history:
            timestamp = datetime.now(ist).strftime("%Y-%m-%d %H:%M:%S")
            sheet_hist.append_row([email, timestamp, q, a])
    except Exception as e:
        st.warning(f"⚠️ Could not save chat history: {e}")

def load_user_chat_history(email):
    try:
        sheet_hist = client.open_by_key(GOOGLE_SHEET_ID).worksheet("chat_history_store")
        records = sheet_hist.get_all_records()
        return [(row["question"], row["answer"]) for row in records if row["email"] == email]
    except Exception as e:
        st.warning(f"⚠️ Could not load chat history: {e}")
        return []

# --- Load/Save Users ---
def load_users():
    try:
        records = sheet.get_all_records()
        return {row["email"]: row["password"] for row in records}
    except Exception as e:
        st.error(f"❌ Error loading users from Google Sheet: {e}")
        return {}

def save_user(email, password):
    email = email.strip().lower()
    hashed = hash_password(password)
    try:
        sheet.append_row([email, hashed])
        st.success("User saved successfully.")
    except Exception as e:
        st.error(f"❌ Error saving user: {e}")

# --- Auth State ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "users" not in st.session_state:
    st.session_state.users = load_users()

# --- Login / Sign Up ---
if not st.session_state.authenticated:
    st.markdown("### 🔐 Sign In or Sign Up")
    option = st.radio("Choose an option:", ["Login", "Sign Up"], horizontal=True)

    email = st.text_input("📧 Email").strip().lower()
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
    else:
        if st.button("Login"):
            valid_credentials = (
                email in st.session_state.users and
                st.session_state.users[email] == hash_password(password)
            )
            if valid_credentials:
                st.session_state.authenticated = True
                st.session_state.email = email
                st.success(f"Welcome back, {email}!")
                st.session_state.chat_history = load_user_chat_history(email)
                st.rerun()
            else:
                st.error("Invalid credentials. Please try again.")
        st.stop()

# --- Logout ---
if st.sidebar.button("🚪 Logout"):
    save_user_chat_history(st.session_state.email, st.session_state.chat_history)
    st.session_state.authenticated = False
    st.session_state.chat_history = []
    st.rerun()

# --- Initialize Chat History ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# --- Show Latest Response ---
if st.session_state.chat_history:
    latest_q, latest_a = st.session_state.chat_history[-1]
    st.markdown("### 🧠 Latest Response")
    st.markdown(f"**You:** {latest_q}")
    st.code(latest_a)  # Uses built-in copy button

if st.session_state.chat_history:
    latest_q, latest_a = st.session_state.chat_history[-1]
    col1, col2 = st.columns(2)

    if col1.button("👍 Helpful", key="feedback_yes"):
        log_feedback(st.session_state.email, latest_q, "Helpful")
        st.success("Thanks for your feedback!")

    if col2.button("👎 Not Helpful", key="feedback_no"):
        log_feedback(st.session_state.email, latest_q, "Not Helpful")
        st.success("Thanks for your feedback!")

# --- Chat Input Form ---
st.markdown("<div class='fixed-bottom-form'>", unsafe_allow_html=True)
with st.form(key="chat_form"):
    user_input = st.text_area("📥 Type your question here:", placeholder="Press ALT+Enter for new line. Press Enter to send.")
    submit = st.form_submit_button("🚀 Ask")

if submit and user_input:
    cleaned_input = user_input.lower().strip()

    greetings = ["hi", "hello", "hey", "yo", "yoo", "hola", "hii", "hiii", "hey there"]
    if cleaned_input in greetings:
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
                raw_answer = response.json()["choices"][0]["message"]["content"]
                answer = re.sub(r'<button.*?</button>', '', raw_answer, flags=re.DOTALL)
                answer = re.sub(r'https?://\S+', '[link removed]', answer)
                st.session_state.chat_history.append((user_input, answer))
                log_chat_to_sheet(st.session_state.email, user_input, answer)
                st.rerun()
            else:
                st.error(f"Error {response.status_code}: {response.text}")
st.markdown("</div>", unsafe_allow_html=True)

# --- Sidebar: History ---
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
        st.success("History cleared.")
    if st.button("⬇️ Export to CSV"):
        df = pd.DataFrame(st.session_state.chat_history, columns=["Question", "Answer"])
        df.to_csv("chat_history.csv", index=False)
        st.success("Exported chat_history.csv")

# --- Footer ---
st.markdown("---")
st.caption("✅ Developed by Glen Dlemos 😎")
