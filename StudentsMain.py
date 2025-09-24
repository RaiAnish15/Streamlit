# app.py
import streamlit as st
import pandas as pd
import numpy as np

# ----------------- Page setup -----------------
st.set_page_config(page_title="Student Performance Dashboard", layout="wide")
st.title("🎓 Student Performance Dashboard")
st.markdown(
    "Upload your CSV to explore performance by **Students**, **Subjects**, and **Gender**."
)

# ----------------- Helpers -----------------
RESERVED_COLS = {
    "StudentID", "Name", "Student", "Batch", "Class", "Year", "Gender"
}

def detect_columns(df: pd.DataFrame):
    """Identify key columns and subject columns robustly."""
    cols = {c.lower(): c for c in df.columns}
    # Try to find name-like column
    name_col = None
    for k in ["name", "student", "student_name"]:
        if k in cols: 
            name_col = cols[k]; break

    # Try to find year & gender
    year_col = None
    for k in ["year", "class_year", "grade_year"]:
        if k in cols:
            year_col = cols[k]; break

    gender_col = None
    for k in ["gender", "sex"]:
        if k in cols:
            gender_col = cols[k]; break

    # Subjects = numeric columns not in reserved set
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    subject_cols = [c for c in numeric_cols if c not in RESERVED_COLS]

    return name_col, year_col, gender_col, subject_cols

def overall_percentage(row: pd.Series, subject_cols):
    # Average across the subject columns for that row (student-year)
    vals = row[subject_cols].astype(float)
    return vals.mean(skipna=True)

def pad_ylim(series: pd.Series, pad=10):
    """Return (ymin, ymax) padded by `pad` while handling single values."""
    s = series.dropna()
    if s.empty:
        return None
    lo, hi = float(s.min()), float(s.max())
    if lo == hi:
        return (lo - pad, hi + pad)
    return (lo - pad, hi + pad)

def center_radio(options, label="View"):
    # Create 3 columns and place radio in the center one
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        return st.radio(label, options, index=None, horizontal=True)

# ----------------- UI: file upload -----------------
uploaded = st.file_uploader("Upload CSV", type=["csv"])

# Show welcome only until file is uploaded
if uploaded is None:
    st.info("👋 Welcome! Please upload your CSV to begin.")
    st.stop()

# Load data
try:
    df = pd.read_csv(uploaded)
except Exception as e:
    st.error(f"Could not read CSV: {e}")
    st.stop()

# Detect key columns
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

# Compute overall percentage for each row (student-year)
if subject_cols:
    df["_OverallPct"] = df.apply(lambda r: overall_percentage(r, subject_cols), axis=1)

# ----------------- Mode selection -----------------
mode = center_radio(["Students", "Subjects", "Gender"], label="Choose a view")
st.divider()

if mode == "Students":
    if name_col is None or year_col is None or not subject_cols:
        st.error("Students view needs a name column, a Year column, and numeric subject columns.")
        st.stop()

    # Student dropdown (None default)
    all_students = sorted(df[name_col].dropna().astype(str).unique().tolist())
    student = st.selectbox("Select a student", options=["— None —"] + all_students, index=0)
    if student == "— None —":
        st.info("Select a student to continue.")
        st.stop()

    # Filter for that student & sort by year
    sdf = df[df[name_col].astype(str) == student].copy()
    if year_col in sdf.columns:
        sdf = sdf.sort_values(by=year_col)

    # What to plot: subject OR overall percentage
    metric_choice = st.selectbox(
        "Plot", 
        options=["— None —", "Overall Percentage"] + subject_cols, 
        index=0
    )
    if metric_choice == "— None —":
        st.info("Select a subject or Overall Percentage to see a plot.")
        st.stop()

    # Build the series
    y = sdf["_OverallPct"] if metric_choice == "Overall Percentage" else sdf[metric_choice]
    x = sdf[year_col] if year_col in sdf.columns else np.arange(len(y))

    st.subheader(f"{student} — {metric_choice}")
    yminmax = pad_ylim(y, pad=5)
    st.line_chart(
        pd.DataFrame({"Year": x, metric_choice: y}).set_index("Year")
    )
    if yminmax:
        st.caption(f"Y-range approx: {round(yminmax[0],1)} to {round(yminmax[1],1)}")

elif mode == "Subjects":
    if year_col is None or not subject_cols:
        st.error("Subjects view needs a Year column and numeric subject columns.")
        st.stop()

    subject = st.selectbox("Select a subject", options=["— None —"] + subject_cols, index=0)
    if subject == "— None —":
        st.info("Select a subject to continue.")
        st.stop()

    # Average yearly marks across all students
    g = df.groupby(year_col)[subject].mean(numeric_only=True).reset_index().sort_values(year_col)
    st.subheader(f"Average yearly marks — {subject}")
    yminmax = pad_ylim(g[subject], pad=5)
    st.line_chart(g.set_index(year_col))
    if yminmax:
        st.caption(f"Y-range approx: {round(yminmax[0],1)} to {round(yminmax[1],1)}")

elif mode == "Gender":
    if gender_col is None or year_col is None or not subject_cols:
        st.error("Gender view needs `Gender`, `Year` and numeric subject columns.")
        st.stop()

    # Gender dropdown
    genders = df[gender_col].dropna().astype(str).unique().tolist()
    genders_sorted = sorted(genders)
    selected_gender = st.selectbox("Select gender", options=["— None —"] + genders_sorted, index=0)
    if selected_gender == "— None —":
        st.info("Select a gender to continue.")
        st.stop()

    # Subject dropdown
    subject = st.selectbox("Select subject", options=["— None —"] + subject_cols, index=0)
    if subject == "— None —":
        st.info("Select a subject to see the plot.")
        st.stop()

    # Compare toggle
    compare = st.checkbox("Compare genders for this subject")

    if compare:
        # Compare all genders for the chosen subject (avg per year)
        comp = (
            df.groupby([year_col, gender_col])[subject]
              .mean(numeric_only=True)
              .reset_index()
              .sort_values([year_col, gender_col])
        )
        st.subheader(f"Yearly average — {subject} (by gender)")
        # Pivot for multi-line chart
        wide = comp.pivot(index=year_col, columns=gender_col, values=subject).sort_index()
        st.line_chart(wide)
        yminmax = pad_ylim(comp[subject], pad=5)
        if yminmax:
            st.caption(f"Y-range approx: {round(yminmax[0],1)} to {round(yminmax[1],1)}")
    else:
        # Single gender average per year for the chosen subject
        g = (
            df[df[gender_col].astype(str) == selected_gender]
            .groupby(year_col)[subject]
            .mean(numeric_only=True)
            .reset_index()
            .sort_values(year_col)
        )
        st.subheader(f"Yearly average — {subject} ({selected_gender})")
        st.line_chart(g.set_index(year_col))
        yminmax = pad_ylim(g[subject], pad=5)
        if yminmax:
            st.caption(f"Y-range approx: {round(yminmax[0],1)} to {round(yminmax[1],1)}")

else:
    # No mode chosen yet
    st.info("Use the radio buttons above to choose **Students**, **Subjects**, or **Gender**.")

# Footer hint
st.divider()
st.caption("Tip: Ensure your CSV has columns like `Name`/`Student`, `Year`, `Gender` (optional), plus numeric subject columns.")
