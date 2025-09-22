# app.py
import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

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
        # return a flat line at mean for overlay (so it renders)
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

def layered_line_with_trend(df_xy, x_col, y_col, title, data_color="#1f77b4", trend_color="#ff7f0e"):
    """
    Build a single Altair chart with the data line and its linear-fit trend line overlaid.
    Colors can be customized; default uses contrasting colors.
    """
    # Ensure sorted by x
    df_xy = df_xy.sort_values(x_col).copy()
    # Compute trend values aligned to x
    y_fit, slope, label = compute_trend_line(df_xy[x_col].values, df_xy[y_col].values)
    df_xy["TrendFit"] = y_fit

    base = alt.Chart(df_xy).encode(
        x=alt.X(x_col, title=x_col)
    )

    data_line = base.mark_line(strokeWidth=3, color=data_color).encode(
        y=alt.Y(y_col, title=y_col),
        tooltip=[x_col, y_col]
    )

    trend_line = base.mark_line(strokeWidth=3, color=trend_color, strokeDash=[6,4]).encode(
        y="TrendFit:Q",
        tooltip=[x_col, alt.Tooltip("TrendFit:Q", title="Trend")]
    )

    chart = alt.layer(data_line, trend_line).properties(
        title=title, height=350
    ).interactive()

    # Caption with slope & label
    st.altair_chart(chart, use_container_width=True)
    st.caption(f"Trend: **{label}** (slope ≈ {slope:.3f} per year)")

def layered_multi_subject_with_trends(avg_df, subjects, x_col="Year"):
    """
    Multi-subject overlay: one line per subject + each subject's trend line in matching color.
    """
    if not subjects:
        st.info("Select at least one subject.")
        return

    # Pivot wide for easier per-subject trend
    wide = avg_df.pivot(index=x_col, columns="Subject", values="Average").sort_index()

    # Build a long dataframe with trend per subject
    layers = []
    color_scale = alt.Scale(scheme="tableau10")  # distinct, high-contrast palette

    # Melt back to long for data lines
    long_data = wide.reset_index().melt(id_vars=[x_col], var_name="Subject", value_name="Average")
    long_data = long_data[long_data["Subject"].isin(subjects)]

    # Data lines
    data_lines = alt.Chart(long_data).mark_line(strokeWidth=3).encode(
        x=alt.X(x_col, title=x_col),
        y=alt.Y("Average:Q", title="Average Marks"),
        color=alt.Color("Subject:N", scale=color_scale),
        tooltip=[x_col, "Subject", alt.Tooltip("Average:Q", format=".2f")]
    )

    # Trend lines: compute per subject
    trend_rows = []
    for sub in subjects:
        y = wide[sub].dropna()
        if len(y) == 0:
            continue
        years = y.index.values.astype(float)
        y_fit, slope, label = compute_trend_line(years, y.values.astype(float))
        tmp = pd.DataFrame({x_col: years, "Trend": y_fit, "Subject": sub})
        trend_rows.append(tmp)
    trend_df = pd.concat(trend_rows, ignore_index=True) if trend_rows else pd.DataFrame(columns=[x_col,"Trend","Subject"])

    trend_lines = alt.Chart(trend_df).mark_line(strokeDash=[6,4], strokeWidth=3).encode(
        x=alt.X(x_col, title=x_col),
        y=alt.Y("Trend:Q", title="Average Marks"),
        color=alt.Color("Subject:N", scale=color_scale),
        tooltip=[x_col, "Subject", alt.Tooltip("Trend:Q", title="Trend", format=".2f")]
    )

    chart = alt.layer(data_lines, trend_lines).properties(
        title="Average Yearly Marks (Selected Subjects) + Trend",
        height=380
    ).interactive()

    st.altair_chart(chart, use_container_width=True)

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

# Detect subjects automatically & compute yearly percentage (mean across detected subjects)
subjects = detect_subject_columns(df)
if len(subjects) == 0:
    st.warning("No subject columns detected (numeric, non-reserved). Please check your CSV.")
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

    # Subject chart (data + trend in one plot)
    if subject in sdf.columns:
        layered_line_with_trend(
            sdf.rename(columns={subject: "Marks"})[["Year","Marks"]],
            x_col="Year", y_col="Marks",
            title=f"{student} — {subject} (Yearly Marks with Trend)",
            data_color="#1f77b4",   # blue
            trend_color="#ff7f0e"   # orange (contrasting)
        )
    else:
        st.info("Selected subject not found in the uploaded file.")

    st.divider()
    if show_pct == "Yes":
        layered_line_with_trend(
            sdf[["Year","Percentage"]],
            x_col="Year", y_col="Percentage",
            title=f"{student} — Yearly Percentage (mean of detected subjects) with Trend",
            data_color="#2ca02c",    # green
            trend_color="#d62728"    # red
        )

# ----------------- Subjects -----------------
elif mode == "Subjects":
    st.markdown("### 📚 Subject-wise Trends (Averages Across All Students)")
    if not subjects:
        st.info("No subject columns detected.")
    else:
        chosen = st.multiselect("Select Subject(s)", subjects, default=subjects[:2])
        # Average by Year for each subject (long df)
        avg_frames = []
        for sub in chosen:
            tmp = df.groupby("Year")[sub].mean().reset_index()
            tmp["Subject"] = sub
            tmp.rename(columns={sub: "Average"}, inplace=True)
            avg_frames.append(tmp)
        if avg_frames:
            avg_df = pd.concat(avg_frames, ignore_index=True)
            layered_multi_subject_with_trends(avg_df, chosen, x_col="Year")
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

        # Average marks by Year and Gender (long)
        gdf = (
            df.groupby(["Year","Gender"])[subj]
            .mean()
            .reset_index()
            .rename(columns={subj: "Average"})
            .sort_values(["Gender","Year"])
        )

        # Build layers: data lines (Male black, Female pink) + trend lines same colors
        # Data lines
        data_line = alt.Chart(gdf).mark_line(strokeWidth=3).encode(
            x=alt.X("Year:Q", title="Year"),
            y=alt.Y("Average:Q", title=f"Average {subj} Marks"),
            color=alt.Color("Gender:N",
                            scale=alt.Scale(domain=["Male","Female"],
                                            range=["black","#ff69b4"])),
            tooltip=["Year","Gender",alt.Tooltip("Average:Q", format=".2f")]
        )

        # Compute trend per gender
        trend_parts = []
        for gender in ["Male","Female"]:
            y = gdf[gdf["Gender"]==gender].dropna(subset=["Average"])
            if len(y) < 2:
                continue
            years = y["Year"].values.astype(float)
            y_fit, slope, label = compute_trend_line(years, y["Average"].values.astype(float))
            trend_parts.append(pd.DataFrame({"Year": years, "Trend": y_fit, "Gender": gender,
                                             "Slope": slope, "Label": label}))
        trend_df = pd.concat(trend_parts, ignore_index=True) if trend_parts else pd.DataFrame(columns=["Year","Trend","Gender","Slope","Label"])

        trend_line = alt.Chart(trend_df).mark_line(strokeDash=[6,4], strokeWidth=3).encode(
            x="Year:Q",
            y="Trend:Q",
            color=alt.Color("Gender:N",
                            scale=alt.Scale(domain=["Male","Female"],
                                            range=["black","#ff69b4"])),
            tooltip=["Year","Gender",alt.Tooltip("Trend:Q", title="Trend", format=".2f")]
        )

        chart = alt.layer(data_line, trend_line).properties(
            title=f"Average Yearly {subj} Marks by Gender (with Trend)",
            height=380
        ).interactive()

        st.altair_chart(chart, use_container_width=True)

        # Show slopes/labels
        if not trend_df.empty:
            summary = (trend_df.groupby("Gender")
                               .agg(Slope=("Slope","first"), Label=("Label","first"))
                               .reset_index())
            summary["Slope"] = summary["Slope"].astype(float).round(3)
            st.table(summary)
