# app.py
import streamlit as st
import pandas as pd
import numpy as np
import altair as alt


st.set_page_config(page_title="Student Performance — Subject View", layout="wide")
st.title("🎓 Student Performance — Subject View")


st.sidebar.header("Upload CSV")
file = st.sidebar.file_uploader("Upload student marks CSV", type=["csv"])
if not file:
    st.info("👋 Welcome! Please upload your CSV to begin.")
    st.stop()

df = pd.read_csv(file)


cols_lower = {c.lower(): c for c in df.columns}
name_col   = cols_lower.get("name", cols_lower.get("student", None))
year_col   = cols_lower.get("year", None)
gender_col = cols_lower.get("gender", cols_lower.get("sex", None))  # not used here, but harmless


reserved = {"studentid", "name", "student", "batch", "class", "year", "gender", "sex"}
numeric_cols = df.select_dtypes(include=["number"]).columns
subject_cols = [c for c in numeric_cols if c.lower() not in reserved]


if name_col is None or year_col is None or len(subject_cols) == 0:
    st.error("Please ensure your CSV has: a Name/Student column, a Year column, and numeric subject columns.")
    st.stop()


df[year_col] = pd.to_numeric(df[year_col], errors="coerce")
df = df.dropna(subset=[year_col]).copy()
df[year_col] = df[year_col].astype(int)


def y_limits(series, pad=5):
    s = pd.to_numeric(series, errors="coerce").dropna()
    if s.empty: return None
    lo, hi = float(s.min()), float(s.max())
    return [lo - pad, hi + pad] if lo != hi else [lo - pad, hi + pad]

def per_year_toppers_subject(full_df, subject_col):
    """Top student per year for the chosen subject (across all students)."""
    idx = full_df.groupby(year_col)[subject_col].idxmax()
    out = full_df.loc[idx, [year_col, name_col, subject_col]].sort_values(year_col)
    out.columns = ["Year", "Top Student", "Score"]
    out["Score"] = out["Score"].round(2)
    return out


student_list = sorted(df[name_col].astype(str).unique())
student = st.sidebar.selectbox("Select a student", ["— None —"] + student_list, index=0)
subject = st.sidebar.selectbox("Select a subject", ["— None —"] + subject_cols, index=0)


if student == "— None —" or subject == "— None —":
    st.info("Use the sidebar to select a **Student** and a **Subject**.")
    st.stop()


subdf = (
    df[df[name_col].astype(str) == student]
    .dropna(subset=[subject])
    .sort_values(year_col)
    .rename(columns={year_col: "Year"})
)

if subdf.empty:
    st.warning(f"No data available for **{student}** in **{subject}**.")
    st.stop()

ylim = y_limits(subdf[subject])

# ===== Plot: student's performance on the chosen subject =====
chart = (
    alt.Chart(subdf)
    .mark_line(point=True)
    .encode(
        x=alt.X("Year:O", axis=alt.Axis(title="Year", format="d")),  # 2000, 2001 (no commas)
        y=alt.Y(f"{subject}:Q", scale=alt.Scale(domain=ylim)),
        tooltip=["Year", subject]
    )
    .properties(title=f"{student} — {subject}")
    .interactive()
)
st.altair_chart(chart, use_container_width=True)


st.subheader(f"🥇 Per-Year Topper — {subject}")
toppers_tbl = per_year_toppers_subject(df.dropna(subset=[subject]), subject)
st.dataframe(toppers_tbl, hide_index=True, use_container_width=True)
