# app.py
import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

# ----------------- Page setup -----------------
st.set_page_config(page_title="Student Performance Dashboard", layout="wide")
st.title("🎓 Student Performance Dashboard")
st.markdown("Upload your CSV to explore performance by **Students**, **Subjects**, and **Gender**.")

# ----------------- Helpers -----------------
RESERVED_COLS = {"StudentID", "Name", "Student", "Batch", "Class", "Year", "Gender"}

def detect_columns(df: pd.DataFrame):
    cols = {c.lower(): c for c in df.columns}
    name_col = next((cols[k] for k in ["name", "student", "student_name"] if k in cols), None)
    year_col = next((cols[k] for k in ["year", "class_year", "grade_year"] if k in cols), None)
    gender_col = next((cols[k] for k in ["gender", "sex"] if k in cols), None)
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    subject_cols = [c for c in numeric_cols if c not in RESERVED_COLS]
    return name_col, year_col, gender_col, subject_cols

def overall_percentage(row: pd.Series, subject_cols):
    vals = row[subject_cols].astype(float)
    return vals.mean(skipna=True)

def y_domain(series: pd.Series, pad=5):
    s = series.dropna()
    if s.empty:
        return None
    lo, hi = float(s.min()), float(s.max())
    if lo == hi:
        lo, hi = lo - pad, hi + pad
    else:
        lo, hi = lo - pad, hi + pad
    return [lo, hi]

def topper_by_year(df, year_col, name_col, value_col):
    """Return dataframe: Year, Top Student, Score for the given value_col."""
    def pick_top(g):
        idx = g[value_col].astype(float).idxmax()
        row = g.loc[idx]
        return pd.Series({"Top Student": row[name_col], "Score": float(row[value_col])})
    out = df.groupby(year_col, as_index=True).apply(pick_top).reset_index()
    out[year_col] = out[year_col].astype(int)
    return out.sort_values(year_col)

def gender_color_map(unique_genders):
    """
    Boys: black (#000000), Girls: pink (#ff4da6), others: contrasting palette.
    Returns (domain, range) lists for Altair.
    """
    domain, rng, used = [], [], set()
    def add(g, color):
        domain.append(g); rng.append(color); used.add(g)

    low = {g: g.lower() for g in unique_genders}
    male_keys = [g for g in unique_genders if low[g].startswith(("m","boy","male"))]
    female_keys = [g for g in unique_genders if low[g].startswith(("f","girl","female"))]

    for g in male_keys:
        if g not in used: add(g, "#000000")
    for g in female_keys:
        if g not in used: add(g, "#ff4da6")

    palette = ["#1f77b4", "#ff7f0e", "#2ca02c", "#8c564b", "#9467bd", "#17becf"]
    p = 0
    for g in unique_genders:
        if g not in used:
            add(g, palette[p % len(palette)])
            p += 1
    return domain, rng

def alt_line(df, x_field, y_field, color_field=None, ydomain=None, title=None,
             color_domain=None, color_range=None, line_color=None):
    """Generic Altair line with integer year axis and optional color mapping."""
    base = alt.Chart(df).mark_line(point=True)

    enc = {
        "x": alt.X(x_field, type="ordinal", axis=alt.Axis(title="Year", format="d")),
        "y": alt.Y(y_field, type="quantitative",
                   scale=alt.Scale(domain=ydomain) if ydomain else alt.Undefined,
                   axis=alt.Axis(title=None)),
    }

    if color_field:
        if color_domain and color_range:
            enc["color"] = alt.Color(color_field, legend=alt.Legend(title=str(color_field)),
                                     scale=alt.Scale(domain=color_domain, range=color_range))
        else:
            enc["color"] = alt.Color(color_field, legend=alt.Legend(title=str(color_field)))

    chart = base.encode(**enc)
    if line_color and not color_field:
        chart = chart.mark_line(point=True, color=line_color)

    if title:
        chart = chart.properties(title=title)

    return chart.interactive()

# ----------------- Upload -----------------
uploaded = st.file_uploader("Upload CSV", type=["csv"])
if uploaded is None:
    st.info("👋 Welcome! Please upload your CSV to begin.")
    st.stop()

try:
    df = pd.read_csv(uploaded)
except Exception as e:
    st.error(f"Could not read CSV: {e}")
    st.stop()

name_col, year_col, gender_col, subject_cols = detect_columns(df)

missing_bits = []
if name_col is None: missing_bits.append("a student name column (e.g., `Name` or `Student`)")
if year_col is None: missing_bits.append("a `Year` column")
if not subject_cols: missing_bits.append("numeric subject columns (e.g., Math, Science...)")

if missing_bits:
    st.warning(
        "I’m expecting: " + "; ".join(missing_bits) +
        ".\n\nTip: Ensure your CSV has columns like `Name`/`Student`, `Year`, `Gender` (optional), and numeric subject columns."
    )

# Clean up year to plain int for axis (avoid 2,000 style)
if year_col is not None:
    df[year_col] = pd.to_numeric(df[year_col], errors="coerce").astype("Int64")
    df = df.dropna(subset=[year_col]).copy()
    df[year_col] = df[year_col].astype(int)

# Compute overall percentage per row (student-year)
if subject_cols:
    df["_OverallPct"] = df.apply(lambda r: overall_percentage(r, subject_cols), axis=1)

# ----------------- Sidebar Controls -----------------
st.sidebar.header("Controls")
mode = st.sidebar.radio("Choose a view", ["Students", "Subjects", "Gender"], index=0)

st.divider()

# ----------------- Views -----------------
if mode == "Students":
    if name_col is None or year_col is None or not subject_cols:
        st.error("Students view needs a name column, a Year column, and numeric subject columns.")
        st.stop()

    all_students = sorted(df[name_col].dropna().astype(str).unique().tolist())
    student = st.sidebar.selectbox("Select a student", options=["— None —"] + all_students, index=0)
    metric_choice = st.sidebar.selectbox("Plot", options=["— None —", "Overall Percentage"] + subject_cols, index=0)

    if student == "— None —":
        st.info("Select a student in the sidebar to continue."); st.stop()
    if metric_choice == "— None —":
        st.info("Select **Overall Percentage** or a **Subject** to see a plot."); st.stop()

    sdf = df[df[name_col].astype(str) == student].copy().sort_values(by=year_col)
    plot_col = "_OverallPct" if metric_choice == "Overall Percentage" else metric_choice
    ydom = y_domain(sdf[plot_col], pad=5)

    chart_df = sdf[[year_col, plot_col]].rename(columns={year_col: "Year", plot_col: metric_choice})
    chart = alt_line(chart_df, x_field="Year", y_field=metric_choice, ydomain=ydom,
                     title=f"{student} — {metric_choice}")
    st.altair_chart(chart, use_container_width=True)

    # Per-year toppers (overall)
    if "_OverallPct" in df.columns:
        st.subheader("🏆 Per-Year Topper — Overall")
        toppers_overall = topper_by_year(df, year_col, name_col, "_OverallPct")
        st.dataframe(toppers_overall.rename(columns={year_col: "Year"}), hide_index=True, use_container_width=True)

    # Per-year toppers for selected subject
    if metric_choice != "Overall Percentage" and metric_choice in subject_cols:
        st.subheader(f"🥇 Per-Year Topper — {metric_choice}")
        toppers_subject = topper_by_year(df.dropna(subset=[metric_choice]), year_col, name_col, metric_choice)
        st.dataframe(toppers_subject.rename(columns={year_col: "Year"}), hide_index=True, use_container_width=True)

elif mode == "Subjects":
    if year_col is None or not subject_cols:
        st.error("Subjects view needs a Year column and numeric subject columns.")
        st.stop()

    subject = st.sidebar.selectbox("Select a subject", options=["— None —"] + subject_cols, index=0)
    if subject == "— None —":
        st.info("Select a subject in the sidebar to continue."); st.stop()

    g = (df.groupby(year_col)[subject].mean(numeric_only=True)
           .reset_index().sort_values(year_col))
    g.columns = ["Year", subject]
    ydom = y_domain(g[subject], pad=5)
    chart = alt_line(g, x_field="Year", y_field=subject, ydomain=ydom,
                     title=f"Average yearly marks — {subject}")
    st.altair_chart(chart, use_container_width=True)

    st.subheader(f"🥇 Per-Year Topper — {subject}")
    toppers_subject = topper_by_year(df.dropna(subset=[subject]), year_col, name_col, subject)
    st.dataframe(toppers_subject.rename(columns={year_col: "Year"}), hide_index=True, use_container_width=True)

    if "_OverallPct" in df.columns:
        st.subheader("🏆 Per-Year Topper — Overall")
        toppers_overall = topper_by_year(df, year_col, name_col, "_OverallPct")
        st.dataframe(toppers_overall.rename(columns={year_col: "Year"}), hide_index=True, use_container_width=True)

elif mode == "Gender":
    if gender_col is None or year_col is None or not subject_cols:
        st.error("Gender view needs `Gender`, `Year` and numeric subject columns.")
        st.stop()

    genders = sorted(df[gender_col].dropna().astype(str).unique().tolist())
    selected_gender = st.sidebar.selectbox("Select gender", options=["— None —"] + genders, index=0)
    subject = st.sidebar.selectbox("Select subject", options=["— None —"] + subject_cols, index=0)
    compare = st.sidebar.checkbox("Compare genders for this subject", value=False)

    if subject == "— None —":
        st.info("Select a subject in the sidebar to continue."); st.stop()

    if compare:
        comp = (
            df.groupby([year_col, gender_col])[subject]
              .mean(numeric_only=True)
              .reset_index()
              .sort_values([year_col, gender_col])
        )
        comp[year_col] = comp[year_col].astype(int)
        comp.rename(columns={year_col: "Year", gender_col: "Gender"}, inplace=True)

        domain, rng = gender_color_map(comp["Gender"].unique().tolist())
        ydom = y_domain(comp[subject], pad=5)

        chart = alt_line(
            comp, x_field="Year", y_field=subject,
            color_field="Gender", ydomain=ydom,
            title=f"Yearly average — {subject} (by gender)",
            color_domain=domain, color_range=rng
        )
        st.altair_chart(chart, use_container_width=True)
    else:
        if selected_gender == "— None —":
            st.info("Select a gender or enable **Compare**."); st.stop()

        g = (
            df[df[gender_col].astype(str) == selected_gender]
            .groupby(year_col)[subject]
            .mean(numeric_only=True)
            .reset_index()
            .sort_values(year_col)
        )
        g.columns = ["Year", subject]
        ydom = y_domain(g[subject], pad=5)

        low = selected_gender.lower()
        if low.startswith(("m","boy","male")):
            line_color = "#000000"
        elif low.startswith(("f","girl","female")):
            line_color = "#ff4da6"
        else:
            line_color = "#1f77b4"

        chart = alt_line(g, x_field="Year", y_field=subject, ydomain=ydom,
                         title=f"Yearly average — {subject} ({selected_gender})",
                         line_color=line_color)
        st.altair_chart(chart, use_container_width=True)

    st.subheader(f"🥇 Per-Year Topper — {subject}")
    toppers_subject = topper_by_year(df.dropna(subset=[subject]), year_col, name_col, subject)
    st.dataframe(toppers_subject.rename(columns={year_col: "Year"}), hide_index=True, use_container_width=True)

    if "_OverallPct" in df.columns:
        st.subheader("🏆 Per-Year Topper — Overall")
        toppers_overall = topper_by_year(df, year_col, name_col, "_OverallPct")
        st.dataframe(toppers_overall.rename(columns={year_col: "Year"}), hide_index=True, use_container_width=True)

# Footer
st.divider()
st.caption("Tip: Ensure your CSV has columns like `Name`/`Student`, `Year`, `Gender` (optional), plus numeric subject columns.")
