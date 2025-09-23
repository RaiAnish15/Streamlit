import streamlit as st

st.set_page_config(page_title="Layout", layout="wide")
st.title("🧱 Layout: Sidebar, Columns, Tabs")

st.sidebar.header("Sidebar Controls")
theme = st.sidebar.radio("Theme", ["Light", "Dark", "Auto"], index=2)
st.sidebar.write("Put global controls here.")

col1, col2, col3 = st.columns([2, 1, 1])
with col1: st.metric("Users", 1280, "+34")
with col2: st.metric("Bounce Rate", "42%", "-2%")
with col3: st.metric("Avg. Time", "3m 12s", "+10s")

tab1, tab2 = st.tabs(["Overview", "Details"])
with tab1:
    st.write("High-level summary...")
with tab2:
    st.write("Fine-grained details...")
