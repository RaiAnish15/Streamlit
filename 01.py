import streamlit as st

st.set_page_config(page_title="Hello Streamlit")

st.title("The first code")
st.subheader("A Basic one")
st.write("This page demonstrates basic text elements.")
st.markdown("""
- **Bold**, *italics*, `code`
- LaTeX: $\\sigma^2 = \\frac{1}{n}\\sum (x_i - \\bar{x})^2$
""")

st.info("ℹ️ This is an info box (blue). Good for tips or notes.")
st.success("✅ This is a success box (green). Use it when something worked!")
st.warning("⚠️ This is a warning box (yellow). Caution, check this step.")
st.error("❌ This is an error box (red). Something went wrong.")


