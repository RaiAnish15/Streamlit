# app.py
import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

# ----------------- Page setup -----------------
st.set_page_config(page_title="Student Performance Dashboard", layout="wide")
st.title("🎓 Student Performance Dashboard")

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
    return row[subject_cols].astype(float).mean(skipna=True)

def y_domain(series: pd.Series, pad=5):
    s = series.dropna()
    if s.empty:
        return None
    lo, hi = float(s.min()), float(s.max())
    return [lo - pad, hi + pad] if lo != hi else [lo - pad, hi + pad]

def topper_by_year(df, year_col, name_col, value_col):
    def pick_top(g):
        idx = g[value_col].astype(float).idxmax()
        row = g.loc[idx]
        return pd.Series({"Top Student": row[name_col], "Score": float(row[value_col])})
    return df.groupby(year_col).apply(pick_top).reset_index()

def gender_color_map(unique_genders):
    domain, rng = [], []
    for g in unique_genders:
        low = g.lower()
        if low.startswith(("m", "boy", "male")):
            domain.append(g); rng.append("#000000")  # black
        elif low.startswith(("f", "girl", "female")):
            domain.append(g); rng.append("#ff4da6")  # pink
        else:
            domain.append(g); rng.append("#1f77b4")  # blue
    return domain, rng

def alt_line(df, x_field, y_field, color_field=None, ydomain=None, title=None,
             color_domain=None, color_range=None, line_color=None):
    base = alt.Chart(df).mark_line(point=True)
    enc = {
        "x": alt.X(x_field, type="ordinal", axis=alt.Axis(title="Year", format="d")),
        "y": alt.Y(y_field, type="quantitative",
                   scale=alt.Scale(domain=ydomain) if ydomain else alt.Undefined),
    }
    if color_field:
        if color_domain and color_range:
            enc["color"] = alt.Color(color_field,
                                     scale=alt.Scale(domain=color_domain, range=color_range),
                                     legend=alt.Legend(title=color_field))
        else:
            enc["color"] = alt.Color(color_field)
    chart = base.encode(**enc)
    if line_color and not color_field:
        chart = chart.mark_line(point=True, color=line_color).encode(**enc)
    return chart.properties(title=title).interactive()

# ----------------- Sidebar: Upload -----------------
st.sidebar.header("Upload CSV")
uploaded = st.sidebar.file_uploader("Upload student marks file", type=["csv"])
if uploaded is None:
    st.info("👋 Welcome! Please upload your CSV to begin.")
    st.stop()

df = pd.read_csv(uploaded)
name_col, year_col, gender_col, subject_cols = detect_columns(df)

if subject_cols:
    df["_OverallPct"] = df.apply(lambda r: overall_percentage(r, subject_cols), axis=1)

# Ensure year is int (no commas)
if year_col:
    df[year_col] = pd.to_numeric(df[year_col], errors="coerce").dropna().astype(int)

# ----------------- Center Radio -----------------
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    mode = st.radio("Choose", ["Students", "Subjects", "Gender"], index=1)

# ----------------- Sidebar Controls -----------------
if mode == "Students":
    student = st.sidebar.selectbox("Select a student", ["— None —"] + sorted(df[name_col].unique()))
    metric_choice = st.sidebar.selectbox("Plot", ["— None —", "Overall Percentage"] + subject_cols)

    if student != "— None —" and metric_choice != "— None —":
        sdf = df[df[name_col] == student].sort_values(year_col)
        plot_col = "_OverallPct" if metric_choice == "Overall Percentage" else metric_choice
        ydom = y_domain(sdf[plot_col], pad=5)
        chart_df = sdf[[year_col, plot_col]].rename(columns={year_col: "Year", plot_col: metric_choice})
        st.altair_chart(alt_line(chart_df, "Year", metric_choice, ydomain=ydom,
                                 title=f"{student} — {metric_choice}"), use_container_width=True)

        st.subheader("🏆 Per-Year Topper — Overall")
        st.dataframe(topper_by_year(df, year_col, name_col, "_OverallPct"), hide_index=True)
        if metric_choice != "Overall Percentage":
            st.subheader(f"🥇 Per-Year Topper — {metric_choice}")
            st.dataframe(topper_by_year(df, year_col, name_col, metric_choice), hide_index=True)

elif mode == "Subjects":
    subject = st.sidebar.selectbox("Select a subject", ["— None —"] + subject_cols)
    if subject != "— None —":
        g = df.groupby(year_col)[subject].mean().reset_index()
        ydom = y_domain(g[subject], pad=5)
        st.altair_chart(alt_line(g, year_col, subject, ydomain=ydom,
                                 title=f"Average yearly marks — {subject}"), use_container_width=True)

        st.subheader(f"🥇 Per-Year Topper — {subject}")
        st.dataframe(topper_by_year(df, year_col, name_col, subject), hide_index=True)

        st.subheader("🏆 Per-Year Topper — Overall")
        st.dataframe(topper_by_year(df, year_col, name_col, "_OverallPct"), hide_index=True)

elif mode == "Gender":
    subject = st.sidebar.selectbox("Select subject", ["— None —"] + subject_cols)
    compare = st.sidebar.checkbox("Compare genders")
    if subject != "— None —":
        if compare:
            comp = df.groupby([year_col, gender_col])[subject].mean().reset_index()
            domain, rng = gender_color_map(comp[gender_col].unique())
            ydom = y_domain(comp[subject], pad=5)
            st.altair_chart(alt_line(comp, year_col, subject, color_field=gender_col,
                                     ydomain=ydom, title=f"{subject} by Gender",
                                     color_domain=domain, color_range=rng),
                            use_container_width=True)
        else:
            gender = st.sidebar.selectbox("Select gender", ["— None —"] + sorted(df[gender_col].unique()))
            if gender != "— None —":
                g = df[df[gender_col] == gender].groupby(year_col)[subject].mean().reset_index()
                ydom = y_domain(g[subject], pad=5)
                color = "#000000" if gender.lower().startswith("m") else "#ff4da6"
                st.altair_chart(alt_line(g, year_col, subject, ydomain=ydom,
                                         title=f"{subject} — {gender}", line_color=color),
                                use_container_width=True)

        st.subheader(f"🥇 Per-Year Topper — {subject}")
        st.dataframe(topper_by_year(df, year_col, name_col, subject), hide_index=True)

        st.subheader("🏆 Per-Year Topper — Overall")
        st.dataframe(topper_by_year(df, year_col, name_col, "_OverallPct"), hide_index=True)
