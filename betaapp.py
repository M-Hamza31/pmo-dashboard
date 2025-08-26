import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="PMO Projects Dashboard", layout="wide")

# Place the logo at the very top of the app
st.image("logo.png", width=100)  # Adjust the path and width as needed

# Use the st.title function for the main heading
st.title("PMO Projects Dashboard")

st.caption("Upload your real dataset (same column names) or use the bundled sample to explore.")

REQUIRED_COLS = [
    "ID","Name","Project Vendor","Project Priority","Business Owner",
    "Project Initiation Date","Target Completion Date","Revised Timeline",
    "Objective","Project Current Status","Project Category","Project Manager","Project Custodian"
]

@st.cache_data
def load_data(file):
    df = pd.read_csv(file)
    # ensure required columns exist
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    # parse dates with the correct format (DD-Mon-YYYY)
    for col in ["Project Initiation Date", "Target Completion Date", "Revised Timeline"]:
        df[col] = pd.to_datetime(df[col], format="%d-%b-%Y", errors="coerce")
    # compute planned end = revised if available else target
    df["Planned End"] = df["Revised Timeline"].fillna(df["Target Completion Date"])
    # overdue flag (not Live/Withdraw and planned end < today)
    today = pd.to_datetime(datetime.today().date())
    df["Overdue"] = (df["Planned End"].notna()) & (df["Planned End"] < today) & (~df["Project Current Status"].isin(["Live","Withdraw"]))
    return df

st.sidebar.header("1) Upload Your CSV")
uploaded = st.sidebar.file_uploader("Upload CSV with the exact columns", type=["csv"])
use_sample = st.sidebar.checkbox("Use bundled sample data", value=not uploaded)

if uploaded is not None and not use_sample:
    df = load_data(uploaded)
else:
    try:
        df = load_data("projects.csv")
    except Exception as e:
        st.error("Sample file not found. Please upload your CSV.")
        st.stop()

# Sidebar filters
st.sidebar.header("2) Filters")
status_sel = st.sidebar.multiselect("Project Current Status", sorted(df["Project Current Status"].dropna().unique().tolist()))
priority_sel = st.sidebar.multiselect("Project Priority", sorted(df["Project Priority"].dropna().unique().tolist()))
category_sel = st.sidebar.multiselect("Project Category", sorted(df["Project Category"].dropna().unique().tolist()))
owner_sel = st.sidebar.multiselect("Business Owner", sorted(df["Business Owner"].dropna().unique().tolist()))
manager_sel = st.sidebar.multiselect("Project Manager", sorted(df["Project Manager"].dropna().unique().tolist()))
vendor_sel = st.sidebar.multiselect("Project Vendor", sorted(df["Project Vendor"].dropna().unique().tolist()))

filtered = df.copy()
if status_sel: filtered = filtered[filtered["Project Current Status"].isin(status_sel)]
if priority_sel: filtered = filtered[filtered["Project Priority"].isin(priority_sel)]
if category_sel: filtered = filtered[filtered["Project Category"].isin(category_sel)]
if owner_sel: filtered = filtered[filtered["Business Owner"].isin(owner_sel)]
if manager_sel: filtered = filtered[filtered["Project Manager"].isin(manager_sel)]
if vendor_sel: filtered = filtered[filtered["Project Vendor"].isin(vendor_sel)]

# KPI row
total_projects = len(filtered)
live_count = (filtered["Project Current Status"] == "Live").sum()
on_hold = (filtered["Project Current Status"] == "On Hold").sum()
withdrawn = (filtered["Project Current Status"] == "Withdraw").sum()
overdue = filtered["Overdue"].sum()

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total Projects", total_projects)
c2.metric("Live", int(live_count))
c3.metric("On Hold", int(on_hold))
c4.metric("Withdrawn", int(withdrawn))
c5.metric("Overdue (not Live/Withdraw)", int(overdue))

st.divider()

# ---------------- NEW Overdue Section ----------------
st.subheader("⚠️ Overdue Projects")

overdue_df = filtered[filtered["Overdue"] == True]

if overdue_df.empty:
    st.success("No overdue projects 🎉")
else:
    # Filters
    col1, col2 = st.columns(2)
    with col1:
        owner_filter = st.selectbox("Filter by Business Owner", ["All"] + sorted(overdue_df["Business Owner"].dropna().unique().tolist()))
    with col2:
        manager_filter = st.selectbox("Filter by Project Manager", ["All"] + sorted(overdue_df["Project Manager"].dropna().unique().tolist()))

    overdue_filtered = overdue_df.copy()
    if owner_filter != "All":
        overdue_filtered = overdue_filtered[overdue_filtered["Business Owner"] == owner_filter]
    if manager_filter != "All":
        overdue_filtered = overdue_filtered[overdue_filtered["Project Manager"] == manager_filter]

    # Show overdue table
    st.dataframe(
        overdue_filtered[[
            "ID", "Name", "Business Owner", "Project Manager",
            "Target Completion Date", "Revised Timeline", "Project Current Status"
        ]],
        use_container_width=True,
        hide_index=True
    )

    # Download overdue CSVs
    st.write("### Download Overdue Projects")
    @st.cache_data
    def to_csv_bytes(df_in):
        return df_in.to_csv(index=False).encode("utf-8")

    st.download_button(
        "Download ALL Overdue Projects (CSV)",
        data=to_csv_bytes(overdue_df[[
            "ID", "Name", "Business Owner", "Project Manager",
            "Target Completion Date", "Revised Timeline", "Project Current Status"
        ]]),
        file_name="overdue_projects_all.csv",
        mime="text/csv"
    )

    st.download_button(
        "Download Filtered Overdue Projects (CSV)",
        data=to_csv_bytes(overdue_filtered[[
            "ID", "Name", "Business Owner", "Project Manager",
            "Target Completion Date", "Revised Timeline", "Project Current Status"
        ]]),
        file_name="overdue_projects_filtered.csv",
        mime="text/csv"
    )

    # Charts for overdue
    st.write("### Overdue Projects by Business Owner")
    owner_counts = overdue_df["Business Owner"].value_counts().reset_index()
    owner_counts.columns = ["Business Owner", "Count"]
    st.bar_chart(owner_counts.set_index("Business Owner"))

    st.write("### Overdue Projects by Project Manager")
    manager_counts = overdue_df["Project Manager"].value_counts().reset_index()
    manager_counts.columns = ["Project Manager", "Count"]
    st.bar_chart(manager_counts.set_index("Project Manager"))
# ---------------- End Overdue Section ----------------

# Charts
left, mid, right = st.columns(3)

with left:
    st.subheader("By Status")
    status_counts = filtered["Project Current Status"].value_counts().reset_index()
    status_counts.columns = ["Project Current Status", "Count"]
    fig_status = px.bar(status_counts, x="Project Current Status", y="Count")
    st.plotly_chart(fig_status, use_container_width=True)

with mid:
    st.subheader("By Priority")
    pr_counts = filtered["Project Priority"].value_counts().reset_index()
    pr_counts.columns = ["Project Priority", "Count"]
    fig_pr = px.pie(pr_counts, names="Project Priority", values="Count")
    st.plotly_chart(fig_pr, use_container_width=True)

with right:
    st.subheader("By Category")
    cat_counts = filtered["Project Category"].value_counts().reset_index()
    cat_counts.columns = ["Project Category", "Count"]
    fig_cat = px.pie(cat_counts, names="Project Category", values="Count")
    st.plotly_chart(fig_cat, use_container_width=True)

st.subheader("Projects per Manager (Top 10)")
mgr_counts = filtered["Project Manager"].value_counts().head(10).reset_index()
mgr_counts.columns = ["Project Manager", "Count"]
fig_mgr = px.bar(mgr_counts, x="Project Manager", y="Count")
st.plotly_chart(fig_mgr, use_container_width=True)

st.subheader("Timeline (Initiation → Planned End)")
show_n = st.slider("How many projects to show on the timeline?", min_value=0, max_value=min(50, len(filtered)), value=min(20, len(filtered)))
timeline_df = filtered.dropna(subset=["Project Initiation Date", "Planned End"]).head(show_n)
if len(timeline_df) > 0:
    fig_tl = px.timeline(
        timeline_df.sort_values("Project Initiation Date"),
        x_start="Project Initiation Date",
        x_end="Planned End",
        y="Name",
        color="Project Current Status",
        hover_data=["ID","Project Priority","Project Manager","Business Owner"]
    )
    fig_tl.update_yaxes(autorange="reversed")
    st.plotly_chart(fig_tl, use_container_width=True)
else:
    st.info("No projects with both start and end dates available in the current filter.")

st.divider()
st.subheader("Filtered Table")
st.dataframe(filtered[REQUIRED_COLS], use_container_width=True, hide_index=True)

st.download_button("Download Filtered CSV", data=to_csv_bytes(filtered[REQUIRED_COLS]), file_name="filtered_projects.csv", mime="text/csv")

st.caption("Tip: Replace the sample CSV with your real export (same column names) to refresh everything automatically.")
st.caption("Created by PMO Intern: Muhammad Hamza")
