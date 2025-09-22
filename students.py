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
    # Subjects = numeric columns not in reserved set (e.g., English, Maths...)
    numeric_cols = df.select_dtypes(include=["number"]).columns
    return [c for c in numeric_cols if c not in RESERVED_COLS]

def compute_yearly_percentage(df, subject_cols):
    df = df.copy()
    if subject_cols:
        df["Percentage"] = df[subject_cols].mean(axis=1)
    else:
        df["Percentage"] = np.nan
    return df

def compute_trend_line(x, y, tol=0.05):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)

    # guard against too-short or constant series
    if len(x) < 2 or np.allclose(y, y[0], equal_nan=False):
        slope = 0.0
        y_fit = np.full_like(y, np.nan, dtype=float)
        label = "Flat →"
        return y_fit, slope, label

    # remove NaNs for robust fit
    mask = ~np.isnan(x) & ~np.isnan(y)
    if mask.sum() < 2:
        slope = 0.0
        y_fit = np.full_like(y, np.nan, dtype=float)
        label = "Flat →"
        return y_fit, slope, label

    coeffs = np.polyfit(x[mask], y[mask], 1)
    slope = float(coeffs[0])
    # evaluate at original x (even where NaN existed, trend line can still show)
    y_fit = np.polyval(coeffs, x)

    if slope > tol:
        label = "Growing ↑"
    elif slope < -tol:
        label = "Falling ↓"
    else:
        label = "Flat →"
    return y_fit, slope, label

def _safe_domain(values, pad=10):
    """build y-axis domain = [min- pad, max + pad], robust to all-NaN or equal min/max."""
    arr = np.asarray(values, dtype=float)
    arr = arr[~np.isnan(arr)]
    if arr.size == 0:
        return [0, 1]  # fallback
    ymin, ymax = float(arr.min()), float(arr.max())
    if np.isclose(ymin, ymax):
        # widen tiny or flat ranges
        ymin -= pad
        ymax += pad
    else:
        ymin -= pad
        ymax += pad
    return [ymin, ymax]

def layered_line_with_trend(df_xy, x_col, y_col, title,
                            data_color="#1f77b4", trend_color="#ff7f0e"):
    """Single Altair chart: data + linear trend overlay, with dynamic y-axis domain."""
    df_xy = df_xy.sort_values(x_col).copy()

    # compute trend
    y_fit, slope, label = compute_trend_line(df_xy[x_col].values, df_xy[y_col].values)
    df_xy["TrendFit"] = y_fit

    # build y-axis domain from both series
    ydomain = _safe_domain(np.r_[df_xy[y_col].values, df_xy["TrendFit"].values], pad=10)

    base = alt.Chart(df_xy).encode(
        x=alt.X(f"{x_col}:Q", title=x_col)
    )

    data_line = base.mark_line(strokeWidth=3, color=data_color).encode(
        y=alt.Y(f"{y_col}:Q", title=y_col, scale=alt.Scale(domain=ydomain)),
        tooltip=[x_col, y_col]
    )

    trend_line = base.mark_line(strokeWidth=3, color=trend_color, strokeDash=[6,4]).encode(
        y=alt.Y("TrendFit:Q", scale=alt.Scale(domain=ydomain)),
        tooltip=[x_col, alt.Tooltip("TrendFit:Q", title="Trend")]
    )

    chart = alt.layer(data_line, trend_line).properties(
        title=title,
        height=360
    ).interactive()

    st.altair_chart(chart, use_container_width=True)
    st.caption(f"Trend: **{label}** (slope ≈ {slope:.3f} per year)")

def layered_multi_subject_with_trends(avg_df, subjects, x_col="Year"):
    """Multi-subject overlay (one color per subject) + each subject's trend in same color."""
    if not subjects:
        st.info("Select at least one subject.")
        return

    wide = avg_df.pivot(index=x_col, columns="Subject", values="Average").sort_index()

    # domain from all selected subjects and their trends
    # first compute trends per subject
    trend_rows = []
    all_vals = []

    for sub in subjects:
        series = wide[sub].dropna()
        if series.empty:
            continue
        years = series.index.values.astype(float)
        y = series.values.astype(float)
        y_fit, slope, label = compute_trend_line(years, y)
        trend_rows.append(pd.DataFrame({x_col: years, "Trend": y_fit, "Subject": sub}))
        all_vals.append(y)
        all_vals.append(y_fit)

    if not trend_rows:
        st.info("Not enough data to compute trends.")
        return

    trend_df = pd.concat(trend_rows, ignore_index=True)
    # include base values too
    long_data = wide.reset_index().melt(id_vars=[x_col], var_name="Subject", value_name="Average")
    long_data = long_data[long_data["Subject"].isin(subjects)]

    all_vals.append(long_data["Average"].values.astype(float))
    ydomain = _safe_domain(np.concatenate([v for v in all_vals if v is not None and len(v) > 0]), pad=10)

    color_scale = alt.Scale(scheme="tableau10")

    data_lines = alt.Chart(long_data).mark_line(strokeWidth=3).encode(
        x=alt.X(f"{x_col}:Q", title=x_col),
        y=alt.Y("Average:Q", title="Average Marks", scale=alt.Scale(domain=ydomain)),
        color=alt.Color("Subject:N", scale=color_scale),
        tooltip=[x_col, "Subject", alt.Tooltip("Average:Q", format=".2f")]
    )

    trend_lines = alt.Chart(trend_df).mark_line(strokeDash=[6,4], strokeWidth=3).encode(
        x=alt.X(f"{x_col}:Q", title=x_col),
        y=alt.Y("Trend:Q", title="Average Marks", scale=alt.Scale(domain=ydomain)),
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

# Detect subjects & compute yearly percentage (mean of detected subjects)
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

    if subject in sdf.columns:
        layered_line_with_trend(
            sdf.rename(columns={subject: "Marks"})[["Year","Marks"]],
            x_col="Year", y_col="Marks",
            title=f"{student} — {subject} (Yearly Marks with Trend)",
            data_color="#1f77b4",   # blue
            trend_color="#ff7f0e"   # orange
        )
    else:
        st.info("Selected subject not found in the uploaded file.")

    st.divider()
    if show_pct == "Yes":
        layered_line_with_trend(
            sdf[["Year","Percentage"]],
            x_col="Year", y_col="Percentage",
            title=f"{student} — Yearly Percentage (mean of detected subjects) with Trend",
            data_color="#2ca02c",   # green
            trend_color="#d62728"   # red
        )

# ----------------- Subjects -----------------
elif mode == "Subjects":
    st.markdown("### 📚 Subject-wise Trends (Averages Across All Students)")
    if not subjects:
        st.info("No subject columns detected.")
    else:
        chosen = st.multiselect("Select Subject(s)", subjects, default=subjects[:2])
        # Average by Year for each chosen subject
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

        # Average marks by Year and Gender
        gdf = (
            df.groupby(["Year","Gender"])[subj]
            .mean()
            .reset_index()
            .rename(columns={subj: "Average"})
            .sort_values(["Gender","Year"])
        )

        # Build y-domain from both genders' data + trends
        trend_parts = []
        all_vals = [gdf["Average"].values.astype(float)]

        for gender in ["Male","Female"]:
            grp = gdf[gdf["Gender"] == gender]
            if len(grp) < 2:
                continue
            years = grp["Year"].values.astype(float)
            yvals = grp["Average"].values.astype(float)
            y_fit, slope, label = compute_trend_line(years, yvals)
            trend_parts.append(pd.DataFrame({
                "Year": years, "Trend": y_fit, "Gender": gender,
                "Slope": slope, "Label": label
            }))
            all_vals.append(y_fit)

        trend_df = pd.concat(trend_parts, ignore_index=True) if trend_parts else pd.DataFrame(columns=["Year","Trend","Gender","Slope","Label"])
        ydomain = _safe_domain(np.concatenate([v for v in all_vals if v is not None and len(v) > 0]), pad=10)

        # Data lines (Male=black, Female=pink)
        data_line = alt.Chart(gdf).mark_line(strokeWidth=3).encode(
            x=alt.X("Year:Q", title="Year"),
            y=alt.Y("Average:Q", title=f"Average {subj} Marks", scale=alt.Scale(domain=ydomain)),
            color=alt.Color("Gender:N",
                            scale=alt.Scale(domain=["Male","Female"],
                                            range=["black","#ff69b4"])),
            tooltip=["Year","Gender",alt.Tooltip("Average:Q", format=".2f")]
        )

        trend_line = alt.Chart(trend_df).mark_line(strokeDash=[6,4], strokeWidth=3).encode(
            x="Year:Q",
            y=alt.Y("Trend:Q", scale=alt.Scale(domain=ydomain)),
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

        # Slope summary table (one row per gender, showing slope/tag used above)
        if not trend_df.empty:
            summary = (trend_df.groupby("Gender")
                               .agg(Slope=("Slope","first"), Label=("Label","first"))
                               .reset_index())
            summary["Slope"] = summary["Slope"].astype(float).round(3)
            st.table(summary)
