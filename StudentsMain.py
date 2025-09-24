# app.py
import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

# ============== PAGE SETUP ==============
st.set_page_config(page_title="Student Performance Dashboard", layout="wide")
st.title("🎓 Student Performance Dashboard")

# ============== SIDEBAR: UPLOAD ==============
st.sidebar.header("Upload CSV")
file = st.sidebar.file_uploader("Upload student marks CSV", type=["csv"])

# Show welcome until upload
if not file:
    st.info("👋 Welcome! Please upload your CSV to begin.")
    st.stop()

# Read CSV
df = pd.read_csv(file)

# ============== BASIC COLUMN DETECTION (KEEP IT SIMPLE) ==============
# Try to find common names for key columns
cols_lower = {c.lower(): c for c in df.columns}
name_col   = cols_lower.get("name", cols_lower.get("student", None))
year_col   = cols_lower.get("year", None)
gender_col = cols_lower.get("gender", cols_lower.get("sex", None))

# Subjects = numeric columns that are not the typical ID/meta columns
reserved = {"studentid", "name", "student", "batch", "class", "year", "gender", "sex"}
numeric_cols = df.select_dtypes(include=["number"]).columns
subject_cols = [c for c in numeric_cols if c.lower() not in reserved]

# Simple safety checks
if name_col is None or year_col is None or len(subject_cols) == 0:
    st.error("Please ensure your CSV has: a Name/Student column, a Year column, and numeric subject columns.")
    st.stop()

# Make Year a clean integer (prevents 2,000 formatting)
df[year_col] = pd.to_numeric(df[year_col], errors="coerce").dropna().astype(int)

# Overall % per row (mean across subject columns)
df["_OverallPct"] = df[subject_cols].mean(axis=1)

# ============== CENTER RADIO (MAIN AREA) ==============
c1, c2, c3 = st.columns([1, 2, 1])
with c2:
    mode = st.radio("Choose a view", ["Students", "Subjects", "Gender"], index=0)

# ============== SMALL UTILS (KEPT INLINE & SIMPLE) ==============
def y_limits(series, pad=5):
    """Return [min-5, max+5] for clearer variation."""
    s = pd.to_numeric(series, errors="coerce").dropna()
    if s.empty:
        return None
    lo, hi = float(s.min()), float(s.max())
    return [lo - pad, hi + pad]

def per_year_toppers(full_df, value_col):
    """
    For each year, find the student with the highest 'value_col'.
    Returns a table with Year, Top Student, Score.
    """
    # idxmax per group -> pick that row
    idx = full_df.groupby(year_col)[value_col].idxmax()
    best = full_df.loc[idx, [year_col, name_col, value_col]].sort_values(year_col)
    best.columns = ["Year", "Top Student", "Score"]
    # Round score for neatness
    best["Score"] = best["Score"].round(2)
    return best

def boys_girls_color(label: str) -> str:
    """Black for boys, pink for girls, a contrasting blue otherwise."""
    if label is None:
        return "#1f77b4"
    low = str(label).lower()
    if low.startswith(("m", "boy", "male")):
        return "#000000"
    if low.startswith(("f", "girl", "female")):
        return "#ff4da6"
    return "#1f77b4"

# ============== VIEWS ==============
if mode == "Students":
    # ---- Controls in sidebar ----
    student_list = sorted(df[name_col].astype(str).unique())
    student = st.sidebar.selectbox("Select a student", ["— None —"] + student_list, index=0)
    metric  = st.sidebar.selectbox("Performance", ["— None —", "Overall Percentage"] + subject_cols, index=0)

    # ---- Guard ----
    if student == "— None —" or metric == "— None —":
        st.info("Use the sidebar to select a student and what to plot.")
        st.stop()

    # ---- Data for chart ----
    subdf = df[df[name_col].astype(str) == student].copy().sort_values(year_col)
    plot_col = "_OverallPct" if metric == "Overall Percentage" else metric
    chart_df = subdf[[year_col, plot_col]].rename(columns={year_col: "Year", plot_col: metric})
    ylim = y_limits(chart_df[metric])

    # ---- Chart (Altair) ----
    chart = (
        alt.Chart(chart_df)
        .mark_line(point=True)
        .encode(
            x=alt.X("Year:O", axis=alt.Axis(title="Year", format="d")),  # no commas
            y=alt.Y(f"{metric}:Q", scale=alt.Scale(domain=ylim)),
            tooltip=["Year", metric]
        )
        .properties(title=f"{student} — {metric}")
        .interactive()
    )
    st.altair_chart(chart, use_container_width=True)

    # ---- Toppers ----
    st.subheader("🏆 Per-Year Topper — Overall")
    st.dataframe(per_year_toppers(df, "_OverallPct"), hide_index=True, use_container_width=True)

    if metric != "Overall Percentage":
        st.subheader(f"🥇 Per-Year Topper — {metric}")
        st.dataframe(per_year_toppers(df.dropna(subset=[metric]), metric),
                     hide_index=True, use_container_width=True)

elif mode == "Subjects":
    # ---- Controls ----
    subject = st.sidebar.selectbox("Select a subject", ["— None —"] + subject_cols, index=0)
    if subject == "— None —":
        st.info("Use the sidebar to pick a subject.")
        st.stop()

    # Average marks per year across all students
    g = df.groupby(year_col)[subject].mean().reset_index().rename(columns={year_col: "Year"})
    ylim = y_limits(g[subject])

    chart = (
        alt.Chart(g)
        .mark_line(point=True)
        .encode(
            x=alt.X("Year:O", axis=alt.Axis(title="Year", format="d")),
            y=alt.Y(f"{subject}:Q", scale=alt.Scale(domain=ylim)),
            tooltip=["Year", subject]
        )
        .properties(title=f"Average yearly marks — {subject}")
        .interactive()
    )
    st.altair_chart(chart, use_container_width=True)

    # Toppers (subject and overall)
    st.subheader(f"🥇 Per-Year Topper — {subject}")
    st.dataframe(per_year_toppers(df.dropna(subset=[subject]), subject),
                 hide_index=True, use_container_width=True)

    st.subheader("🏆 Per-Year Topper — Overall")
    st.dataframe(per_year_toppers(df, "_OverallPct"),
                 hide_index=True, use_container_width=True)

elif mode == "Gender":
    # ---- Controls ----
    subject = st.sidebar.selectbox("Select subject", ["— None —"] + subject_cols, index=0)
    compare = st.sidebar.checkbox("Compare genders", value=False)

    if subject == "— None —":
        st.info("Use the sidebar to pick a subject (and compare if you want).")
        st.stop()

    if compare:
        # Multi-gender comparison lines
        comp = df.groupby([year_col, gender_col])[subject].mean().reset_index()
        comp = comp.rename(columns={year_col: "Year", gender_col: "Gender"})
        ylim = y_limits(comp[subject])

        # Color scale: boys black, girls pink, others blue
        unique_g = comp["Gender"].dropna().astype(str).unique().tolist()
        domain = unique_g
        range_ = [boys_girls_color(g) for g in unique_g]

        chart = (
            alt.Chart(comp)
            .mark_line(point=True)
            .encode(
                x=alt.X("Year:O", axis=alt.Axis(title="Year", format="d")),
                y=alt.Y(f"{subject}:Q", scale=alt.Scale(domain=ylim)),
                color=alt.Color("Gender:N", scale=alt.Scale(domain=domain, range=range_), legend=alt.Legend(title="Gender")),
                tooltip=["Year", "Gender", subject]
            )
            .properties(title=f"Yearly average — {subject} (by gender)")
            .interactive()
        )
        st.altair_chart(chart, use_container_width=True)

    else:
        # Single gender line
        gender_list = sorted(df[gender_col].astype(str).unique())
        gender = st.sidebar.selectbox("Select gender", ["— None —"] + gender_list, index=0)
        if gender == "— None —":
            st.info("Pick a gender or enable Compare.")
            st.stop()

        g = (
            df[df[gender_col].astype(str) == gender]
            .groupby(year_col)[subject].mean().reset_index()
            .rename(columns={year_col: "Year"})
        )
        ylim = y_limits(g[subject])

        chart = (
            alt.Chart(g)
            .mark_line(point=True, color=boys_girls_color(gender))
            .encode(
                x=alt.X("Year:O", axis=alt.Axis(title="Year", format="d")),
                y=alt.Y(f"{subject}:Q", scale=alt.Scale(domain=ylim)),
                tooltip=["Year", subject]
            )
            .properties(title=f"Yearly average — {subject} ({gender})")
            .interactive()
        )
        st.altair_chart(chart, use_container_width=True)

    # Toppers (subject + overall across whole dataset)
    st.subheader(f"🥇 Per-Year Topper — {subject}")
    st.dataframe(per_year_toppers(df.dropna(subset=[subject]), subject),
                 hide_index=True, use_container_width=True)

    st.subheader("🏆 Per-Year Topper — Overall")
    st.dataframe(per_year_toppers(df, "_OverallPct"),
                 hide_index=True, use_container_width=True)
