import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Data & Charts", layout="wide")
st.title("Data ➜ Table ➜ Chart")

# Tiny demo DataFrame
df = pd.DataFrame({
    "x": np.arange(1, 21),
    "y": np.random.randn(20).cumsum()
})

view = st.radio("Pick a chart type", ["Line", "Bar"], horizontal=True)
st.subheader("Data preview")
st.dataframe(df, use_container_width=True)

st.subheader(f"{view} chart")
if view == "Line":
    st.line_chart(df, x="x", y="y")
else:
    st.bar_chart(df, x="x", y="y")
