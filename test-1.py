import streamlit as st

st.set_page_config(page_title="Class 1 – Streamlit Basics")

st.title("Hello! Welcome to Streamlit. This is test-1")


name = st.text_input("Enter your name:","Enter")
st.write(f"Welcome, **{name}**!")

