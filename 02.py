import streamlit as st
import time

st.set_page_config(page_title="Widgets 101", layout="wide")
st.title("🎛️ Widgets & Instant Feedback")

name = st.text_input("Your name", placeholder="Type here...")
level = st.selectbox("Your experience level", ["Beginner", "Intermediate", "Advanced"])
age = st.slider("Your age", 10, 70, 25)
show_more = st.checkbox("Show more details")

st.write(f"👋 Hi **{name or 'friend'}**! You selected **{level}** and age **{age}**.")

if show_more:
    st.success("This is a conditional block controlled by the checkbox.")

with st.expander("Why Streamlit reruns?"):
    st.write("Every widget interaction reruns the script from top to bottom with current widget values.")


