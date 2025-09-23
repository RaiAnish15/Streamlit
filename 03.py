import streamlit as st
import pandas as pd

st.set_page_config(page_title="Layout Demo", layout="wide")
st.title("📊 Student Marks Dashboard")

# ---------------- Sidebar ----------------
st.sidebar.header("Filters")
class_selected = st.sidebar.selectbox("Select Class", ["Class 10", "Class 11", "Class 12"])
subject_selected = st.sidebar.radio("Subject", ["Math", "Science", "English"], index=0)
st.sidebar.write("Sidebar is great for filters and global controls!")

# ---------------- Dummy Data ----------------
data = {
    "Student": ["Alice", "Bob", "Charlie", "David"],
    "Math": [85, 70, 90, 60],
    "Science": [78, 82, 88, 74],
    "English": [92, 80, 75, 85],
}
df = pd.DataFrame(data)

# ---------------- Columns ----------------
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Students", len(df))
with col2:
    st.metric("Average Marks", round(df[subject_selected].mean(), 1))
with col3:
    st.metric("Highest Marks", df[subject_selected].max())

# ---------------- Tabs ----------------
tab1, tab2 = st.tabs(["Table View", "Summary"])
with tab1:
    st.subheader(f"Marks in {subject_selected}")
    st.dataframe(df[["Student", subject_selected]])
with tab2:
    st.subheader("Summary Statistics")
    st.write(df.describe())
