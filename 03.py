import streamlit as st
import pandas as pd

st.set_page_config(page_title="Student Dashboard", layout="wide")
st.title("📚 Multi-Class Student Marks Dashboard")

class_data = {
    "Class 10": pd.DataFrame({
        "Student": ["Alice", "Bob", "Charlie", "David"],
        "Math": [85, 70, 90, 60],
        "Science": [78, 82, 88, 74],
        "English": [92, 80, 75, 85],
    }),
    "Class 11": pd.DataFrame({
        "Student": ["Eva", "Frank", "Grace"],
        "Math": [88, 67, 95],
        "Physics": [91, 73, 89],
        "Chemistry": [84, 69, 92],
    }),
    "Class 12": pd.DataFrame({
        "Student": ["Henry", "Ivy", "Jack", "Karan", "Lily"],
        "Math": [90, 85, 76, 88, 95],
        "Physics": [89, 80, 70, 92, 97],
        "Chemistry": [93, 78, 74, 85, 99],
        "English": [87, 91, 79, 88, 94],
    })
}


st.sidebar.header("Filters")
cls_selected = st.sidebar.selectbox("Select Class", ["(None)"] + list(class_data.keys()))


if cls_selected == "(None)":
    st.info("👋 Welcome! Please select a class from the sidebar to continue.")
    st.stop()


df = class_data[cls_selected]
subjects = [c for c in df.columns if c != "Student"]
subject = st.sidebar.selectbox("Select Subject", ["(None)"] + subjects)


if subject == "(None)":
    st.info(f"✅ You selected **{cls_selected}**. Now pick a **Subject** from the sidebar to see results.")
    st.stop()


st.subheader(f"📊 Marks for {cls_selected}")
st.dataframe(df, use_container_width=True)

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Avg Marks", round(df[subject].mean(), 1))
with col2:
    st.metric("Max Marks", int(df[subject].max()))
with col3:
    st.metric("Min Marks", int(df[subject].min()))

tab1, tab2 = st.tabs(["Summary", "Chart"])
with tab1:
    st.write(df.describe().T)
with tab2:
    st.bar_chart(df.set_index("Student")[subject])
