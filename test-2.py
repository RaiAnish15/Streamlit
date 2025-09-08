import streamlit as st

st.set_page_config(page_title="Widgets & Reruns", layout="wide")
st.title("Widgets & Reactive Reruns")

st.write("Try changing these inputs and notice the app updates automatically.")

colA, colB = st.columns(2)
with colA:
    age = st.slider("Your age", 10, 70, 25)
with colB:
    level = st.selectbox("Experience level", ["Beginner", "Intermediate", "Advanced"])

st.write(f"🎯 You are {age} years old and {level} with Streamlit.")
st.info("Streamlit re-runs top-to-bottom on every interaction.")
st.success("This is a success message (green box).")
st.warning("This is a warning message (yellow box).")
st.error("This is an error message (red box).")
