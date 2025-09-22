# app.py
import streamlit as st
import pandas as pd
import numpy as np

# ----------------- Utilities -----------------
RESERVED_COLS = {"StudentID","Name","Batch","Class","Year","Gender"}

def load_data(uploaded_file=None, fallback_path="batch2000_student_marks_with_gender.csv"):
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
    else:
        try:
            df = pd.read_csv(fallback_path)
        except Exception:
            st.error("No CSV found. Please upload your data file.")
            st.stop()
    return df

def detect_subject_columns(df):
    # Subjects = numeric columns not in reserved set
    numeric_cols = df.select_dtypes(include=["number"]).columns
    subject_cols = [c for c in numeric_cols if c not in RESERVED_COLS]
    # If Year is numeric, it's excluded by reserved set
    return subject_cols

def compute_yearly_percentage(df, subject_cols):
    if not subject_cols:
        df["Percentage"] = np.nan
    else:
        df["Percentage"] = df[subject_cols].mean(axis=1)
    return df

def compute_trend_line(x, y, tol=0.05):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if len(x) < 2 or np.allclose(y, y[0]):
        slope = 0.0
        y_fit = np.full_like(y, np.nan, dtype=float)
        label = "Flat →"
        return y_fit, slope, label
    coeffs = np.polyfit(x, y, 1)
    slope = float(coeffs[0])
    y_fit = np.polyval(coeffs, x)
    if slope > tol:
        label = "Growing ↑"
    elif slope < -tol:
        label = "Falling ↓"
    else:
        label = "Flat →"
    return y_fit, slope, label

def plot_with_trend(df_xy, x_col, y_col, title):
    st.subheader(title)
    st.line_chart(df_xy.set_index(x_col)[y_col])
    y_fit, slope, label = compute_trend_line(df_xy[x_col].values, df_xy[y_col].values)
    overlay = pd.DataFrame({x_col: df_xy[x_col].values, "Trend (linear fit)": y_fit}).set_index(x_col)
    st.line_chart(overlay)
    st.caption(f"Trend: **{label}** (slope ≈ {slope:.3f} per year)")

# ----------------- App -----------------
st.set_page_config(page_title="Student Performance Dashboard", layout="wide")
st.title("📊 Student Performance Dashboard")

with st.sidebar:
    st.header("Load Data")
    up = st.file_uploader("Upload CSV", type=["csv"])
    st.caption("If not uploaded, the app will use 'batch2000_student_marks_with_gender.csv' in the app folder.")

df = load_data(up)
# Basic guards
needed = {"Name","Class","Year"}
missing = needed - set(df.columns)
if missing:
    st.error(f"Missing required columns: {missing}")
    st.stop()

# Detect subjects automatically
subjects = detect_subject_columns(df)
if len(subjects) == 0:
    st.warning("No subject columns detected (numeric, non-reserved). Please check your CSV.")
# Compute yearly percentage = mean across all detected subject columns
df = compute_yearly_percentage(df.copy(), subjects)

mode = st.radio("View by:", ["Students", "Subjects", "Gender"], horizontal=True)

# ----------------- Students -----------------
if mode == "Students":
    st.markdown("### 🎓 Student-wise Exploration")
    c1, c2, c3 = st.columns([2,2,2])
    with c1:
        student = st.selectbox("Select Student", sorted(df["Name"].unique()))
    with c2:
        subject = st.selectbox("Select Subject", subjects if subjects else ["(none)"])
    with c3:
        show_pct = st.selectbox("Show Yearly Percentage Trend?", ["Yes", "No"], index=0)

    sdf = df[df["Name"] == student].sort_values("Year")
    # Subject chart
    if subject in sdf.columns:
        plot_with_trend(
            sdf.rename(columns={subject: "Marks"})[["Year","Marks"]],
            x_col="Year", y_col="Marks",
            title=f"{student} — {subject} (Yearly Marks + Trend)"
        )
    else:
        st.info("Selected subject not found in the uploaded file.")

    st.divider()
    if show_pct == "Yes":
        plot_with_trend(
            sdf[["Year","Percentage"]],
            x_col="Year", y_col="Percentage",
            title=f"{student} — Yearly Percentage (mean of detected subjects) + Trend"
        )

# ----------------- Subjects -----------------
elif mode == "Subjects":
    st.markdown("### 📚 Subject-wise Trends (Averages Across All Students)")
    if not subjects:
        st.info("No subject columns detected.")
    else:
        chosen = st.multiselect("Select Subject(s)", subjects, default=subjects[:2])
        # Average by Year for each subject
        avg_frames = []
        for sub in chosen:
            tmp = df.groupby("Year")[sub].mean().reset_index()
            tmp["Subject"] = sub
            tmp.rename(columns={sub: "Average"}, inplace=True)
            avg_frames.append(tmp)
        if avg_frames:
            avg_df = pd.concat(avg_frames, ignore_index=True)
            wide = avg_df.pivot(index="Year", columns="Subject", values="Average").sort_index()
            st.line_chart(wide)
            # Trend table
            rows = []
            for sub in chosen:
                y = wide[sub].dropna()
                if len(y) == 0: 
                    continue
                y_fit, slope, label = compute_trend_line(y.index.values, y.values)
                rows.append({"Subject": sub, "Trend": label, "Slope (marks/year)": round(float(slope),3)})
            if rows:
                st.table(pd.DataFrame(rows))
        else:
            st.info("Select at least one subject to view trends.")

# ----------------- Gender -----------------
else:
    st.markdown("### 👥 Gender-wise Comparison")
    if "Gender" not in df.columns:
        st.info("No 'Gender' column found in the dataset.")
    elif not subjects:
        st.info("No subject columns detected.")
    else:
        subj = st.selectbox("Select Subject", subjects)
        gdf = (
            df.groupby(["Year","Gender"])[subj]
            .mean().reset_index().rename(columns={subj: "Average"})
        )
        wide = gdf.pivot(index="Year", columns="Gender", values="Average").sort_index()
        st.subheader(f"Average Yearly {subj} Marks by Gender")
        st.line_chart(wide)

        # Trend per gender
        rows = []
        for gender in wide.columns:
            y = wide[gender].dropna()
            if len(y) == 0:
                continue
            _, slope, label = compute_trend_line(y.index.values, y.values)
            rows.append({"Gender": gender, "Trend": label, "Slope (marks/year)": round(float(slope),3)})
        if rows:
            st.table(pd.DataFrame(rows))
