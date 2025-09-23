import streamlit as st

st.set_page_config(page_title="Hello Streamlit")

st.title("The first code")
st.subheader("A Basic one")
st.write("This page demonstrates basic text elements.")
st.markdown("""
- **Bold**, *italics*, `code`
- LaTeX: $\\sigma^2 = \\frac{1}{n}\\sum (x_i - \\bar{x})^2$
""")

st.info("Tip: Run me with `streamlit run app_01_hello.py`")
