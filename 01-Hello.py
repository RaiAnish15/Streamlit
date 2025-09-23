import streamlit as st

st.set_page_config(page_title="Hello Streamlit", page_icon="👋", layout="centered")

st.title("Hello, Streamlit")
st.subheader("From Python script → interactive web app")
st.write("This page demonstrates basic text elements.")
st.markdown("""
- **Bold**, *italics*, `code`
- LaTeX: $\\sigma^2 = \\frac{1}{n}\\sum (x_i - \\bar{x})^2$
""")

st.info("Tip: Run me with `streamlit run app_01_hello.py`")
