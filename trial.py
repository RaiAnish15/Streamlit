# app.py — Student Marks Dashboard (beginner‑friendly)
# --------------------------------------------------
# Teaching goals:
# 1) Show a simple, visual dashboard students instantly relate to.
# 2) Keep code readable: small functions, clear comments, minimal libraries.
# 3) Work even without any external file (ships with a tiny demo dataset).

import io
import pandas as pd
import numpy as np
import streamlit as st

# ---------- Page setup ----------
st.set_page_config(page_title="Student Marks Dashboard", page_icon="🎓", layout="wide")
st.title("🎓 Student Marks Dashboard")
st.caption("Filter marks by class, subject, and range — then explore tables & charts.")

# ---------- Demo data (used when no file is uploaded) ----------
DEMO_DF = pd.DataFrame(
    {
        "Name": [
            "Aarav", "Aarav", "Aarav", "Isha", "Isha", "Isha", "Kabir", "Kabir", "Kabir",
            "Meera", "Meera", "Meera", "Rohan", "Rohan", "Rohan"
        ],
        "Class": ["10A", "10A", "10A", "10A", "10A", "10A", "10B", "10B", "10B", "10B", "10B", "10B", "10C", "10C", "10C"],
        "Subject": [
            "Maths", "Science", "English",
            "Maths", "Science", "English",
            "Maths", "Science", "English",
            "Maths", "Science", "English",
            "Maths", "Science", "English",
        ],
        "Marks": [88, 79, 92, 76, 71, 84, 90, 83, 78, 69, 74, 81, 95, 72, 68],
        "Date": pd.to_datetime([
            "2025-07-01", "2025-07-01", "2025-07-01",
            "2025-07-01", "2025-07-01", "2025-07-01",
            "2025-07-08", "2025-07-08", "2025-07-08",
            "2025-07-15", "2025-07-15", "2025-07-15",
            "2025-07-22", "2025-07-22", "2025-07-22",
        ]),
    }
)

# ---------- Helpers ----------
@st.cache_data(show_spinner=False)
def load_csv(file) -> pd.DataFrame:
    """Load a CSV (uploaded by user) with minimal type handling."""
    df = pd.read_csv(file)
    # Normalize column names to expected set if possible
    colmap = {c.lower().strip(): c for c in df.columns}
    # Required columns (case-insensitive match): Name, Class, Subject, Marks, Date(optional)
    # Try to find likely matches
    def find_col(*cands):
        for key, orig in colmap.items():
            if key in [c.lower() for c in cands]:
                return orig
        return None

    name_c = find_col("name") or "Name"
    class_c = find_col("class", "section") or "Class"
    subj_c = find_col("subject", "course") or "Subject"
    marks_c = find_col("marks", "score") or "Marks"
    date_c = find_col("date", "exam_date")  # optional

    # Rename if needed (only if those exist)
    rename = {}
    if name_c in df.columns and name_c != "Name":
        rename[name_c] = "Name"
    if class_c in df.columns and class_c != "Class":
        rename[class_c] = "Class"
    if subj_c in df.columns and subj_c != "Subject":
        rename[subj_c] = "Subject"
    if marks_c in df.columns and marks_c != "Marks":
        rename[marks_c] = "Marks"
    if date_c and date_c in df.columns and date_c != "Date":
        rename[date_c] = "Date"

    if rename:
        df = df.rename(columns=rename)

    # Keep only known columns if present
    keep = [c for c in ["Name", "Class", "Subject", "Marks", "Date"] if c in df.columns]
    df = df[keep]

    # Type cleaning
    if "Marks" in df.columns:
        df["Marks"] = pd.to_numeric(df["Marks"], errors="coerce")
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    # Drop fully empty rows
    return df.dropna(how="all").reset_index(drop=True)


def use_data() -> pd.DataFrame:
    """Get data from uploader if provided; else fall back to demo."""
    st.sidebar.header("📁 Data")
    up = st.sidebar.file_uploader("Upload a CSV with columns: Name, Class, Subject, Marks, Date(optional)", type=["csv"])
    if up is None:
        st.sidebar.info("Using demo data (upload your CSV to replace).")
        return DEMO_DF.copy()
    try:
        return load_csv(up)
    except Exception as e:
        st.sidebar.error(f"Could not read CSV: {e}")
        return DEMO_DF.copy()


# ---------- Load data ----------
df = use_data()

if df.empty:
    st.warning("No data rows available. Please upload a CSV or use the demo.")
    st.stop()

# Ensure required columns exist
required = {"Name", "Class", "Subject", "Marks"}
missing = required - set(df.columns)
if missing:
    st.error(f"Missing required columns: {', '.join(sorted(missing))}")
    st.stop()

# ---------- Sidebar filters ----------
st.sidebar.header("🔎 Filters")
classes = sorted(df["Class"].dropna().astype(str).unique())
subjects = sorted(df["Subject"].dropna().astype(str).unique())

class_sel = st.sidebar.selectbox("Class", options=["All"] + classes, index=0)
subj_sel = st.sidebar.multiselect("Subjects", options=subjects, default=subjects)

min_m = int(np.nanmin(df["Marks"])) if not df["Marks"].isna().all() else 0
max_m = int(np.nanmax(df["Marks"])) if not df["Marks"].isna().all() else 100
mark_range = st.sidebar.slider("Marks range", min_value=min_m, max_value=max_m, value=(min_m, max_m))

# ---------- Apply filters ----------
mask = (
    df["Marks"].between(mark_range[0], mark_range[1], inclusive="both") &
    df["Subject"].isin(subj_sel)
)
if class_sel != "All":
    mask &= df["Class"].astype(str).eq(class_sel)

fdf = df.loc[mask].copy()

# ---------- KPIs ----------
left, mid, right, extra = st.columns(4)
with left:
    st.metric("Rows (filtered)", fdf.shape[0])
with mid:
    st.metric("Avg Marks", f"{fdf['Marks'].mean():.1f}" if not fdf.empty else "—")
with right:
    st.metric("Highest", f"{fdf['Marks'].max():.0f}" if not fdf.empty else "—")
with extra:
    st.metric("Lowest", f"{fdf['Marks'].min():.0f}" if not fdf.empty else "—")

st.divider()

# ---------- Table ----------
st.subheader("📋 Filtered Table")
st.dataframe(fdf, use_container_width=True, hide_index=True)

# ---------- Charts ----------
col1, col2 = st.columns(2)

with col1:
    st.markdown("**Average Marks by Subject**")
    if not fdf.empty:
        avg_by_subj = fdf.groupby("Subject", as_index=False)["Marks"].mean().sort_values("Marks", ascending=False)
        st.bar_chart(avg_by_subj, x="Subject", y="Marks")
    else:
        st.info("No data for the current filters.")

with col2:
    st.markdown("**Top Students (by Mean Marks)**")
    if not fdf.empty:
        top_students = (
            fdf.groupby("Name", as_index=False)["Marks"].mean()
            .rename(columns={"Marks": "MeanMarks"})
            .sort_values("MeanMarks", ascending=False)
            .head(10)
        )
        st.bar_chart(top_students, x="Name", y="MeanMarks")
    else:
        st.info("No data for the current filters.")

st.divider()

# ---------- Optional: Time trend for one student ----------
st.markdown("**Marks Over Time (Select a Student)**")
if "Date" in fdf.columns and not fdf["Date"].isna().all():
    student_names = sorted(fdf["Name"].dropna().astype(str).unique())
    sel_student = st.selectbox("Student", options=student_names)
    ts = fdf.loc[fdf["Name"].astype(str).eq(sel_student)].sort_values("Date")
    if not ts.empty:
        st.line_chart(ts, x="Date", y="Marks")
else:
    st.caption("(Add a Date column to your CSV to see time trends.)")

# ---------- Download filtered data ----------
@st.cache_data(show_spinner=False)
def to_csv_bytes(_df: pd.DataFrame) -> bytes:
    return _df.to_csv(index=False).encode("utf-8")

st.download_button(
    label="⬇️ Download filtered CSV",
    data=to_csv_bytes(fdf),
    file_name="filtered_marks.csv",
    mime="text/csv",
)

# ---------- Teaching Notes (for you) ----------
# • st.set_page_config(): sets title, icon, layout.
# • Sidebar: file_uploader + filters; Main: KPIs → Table → Charts → Download.
# • @st.cache_data: caches expensive functions (CSV read, conversions) to speed reruns.
# • Groupby and basic charts demonstrate the pandas → visualization loop students will use often.
# • The app degrades gracefully: if the user provides no file / wrong columns, it explains what to fix.
