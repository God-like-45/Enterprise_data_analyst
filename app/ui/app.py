import streamlit as st
import requests
import pandas as pd
import os
from dotenv import load_dotenv
load_dotenv()

# 1. Configure the page
st.set_page_config(page_title="Enterprise Data Analyst", page_icon="🤖", layout="wide")

# 2. Authentication Gate
def check_password():
    """Returns `True` if the user had the correct password."""
    def password_entered():
        if st.session_state["password"] == os.getenv("UI_PASSWORD", "admin"):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store password in session
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct", False):
        return True

    st.title("🔒 Enterprise Login Required")
    st.text_input(
        "Please enter your password to access the AI Data Analyst", 
        type="password", 
        on_change=password_entered, 
        key="password"
    )
    if "password_correct" in st.session_state:
        st.error("😕 Password incorrect")
    return False

# 3. Main Application Logic
if check_password():
    st.title("🤖 Enterprise AI Data Analyst")
    st.markdown("Ask questions in plain English, and the AI will query the PostgreSQL database for you.")

    API_URL = "http://127.0.0.1:8000/api/v1/query"

    if "messages" not in st.session_state:
        st.session_state.messages = []

    def render_chart_if_possible(df: pd.DataFrame):
        """Forces a bar chart render if we have exactly two columns: one text, one numeric."""
        if df.shape[1] == 2:
            try:
                numeric_col = df.select_dtypes(include=['number']).columns
                text_col = df.select_dtypes(exclude=['number']).columns
                
                if len(numeric_col) == 1 and len(text_col) == 1:
                    chart_data = df.set_index(text_col[0])
                    st.bar_chart(chart_data[numeric_col[0]])
            except Exception:
                pass

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("data"):
                df = pd.DataFrame(message["data"])
                st.dataframe(df)
                render_chart_if_possible(df)
            if message.get("sql"):
                with st.expander("View Generated SQL"):
                    st.code(message["sql"], language="sql")

    if prompt := st.chat_input("E.g., Show me total revenue by category."):
        
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("assistant"):
            with st.spinner("Analyzing data and generating charts..."):
                try:
                    response = requests.post(API_URL, json={"question": prompt})
                    response.raise_for_status()
                    result = response.json()
                    
                    if result.get("success"):
                        st.markdown("Here is the data you requested:")
                        
                        if result.get("data"):
                            df = pd.DataFrame(result["data"])
                            st.dataframe(df)
                            render_chart_if_possible(df.copy())
                        else:
                            st.info("The query ran successfully, but returned no data.")
                            
                        with st.expander("View Generated SQL"):
                            st.code(result.get("generated_sql"), language="sql")
                            
                        st.session_state.messages.append({
                            "role": "assistant", 
                            "content": "Here is the data you requested:",
                            "data": result.get("data"),
                            "sql": result.get("generated_sql")
                        })
                    else:
                        error_msg = f"Error: {result.get('error')}"
                        st.error(error_msg)
                        st.session_state.messages.append({"role": "assistant", "content": error_msg})
                        
                except requests.exceptions.ConnectionError:
                    st.error("Cannot connect to the backend API. Is the FastAPI server running?")