import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import time

st.set_page_config(page_title="Customer Support Dashboard", page_icon="🎯", layout="wide")

API_TOKEN = st.secrets["MONDAY_API_TOKEN"]
BOARD_ID = st.secrets.get("MONDAY_BOARD_ID", "5098274792")

PRIORITY_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
PRIORITY_COLORS = {"Critical": "#A32D2D", "High": "#E24B4A", "Medium": "#EF9F27", "Low": "#639922"}

COLUMN_MAP = {
    "status": "Status",
    "priority": "Priority",
    "customer": "Customer",
    "issue_type": "Issue Type",
    "resolution_type": "Resolution Type",
    "date_closed": "Date Closed",
    "numbers": "Time Spent (minutes)",
    "customer_issue_verified": "Customer Issue Verified",
    "issue_source": "Issue Source",
    "open_by": "Open By",
    "detailed_description": "Detailed Description",
}

@st.cache_data(ttl=60)
def fetch_monday_data():
    query = """
    {
      boards(ids: %s) {
        items_page(limit: 500) {
          items {
            name
            column_values {
              id
              text
            }
          }
        }
      }
    }
    """ % BOARD_ID

    response = requests.post(
        "https://api.monday.com/v2",
        json={"query": query},
        headers={
            "Authorization": API_TOKEN,
            "Content-Type": "application/json",
            "API-Version": "2024-01"
        }
    )
    data = response.json()
    items = data["data"]["boards"][0]["items_page"]["items"]
    rows = []
    for item in items:
        row = {"Name": item["name"]}
        for col in item["column_values"]:
            label = COLUMN_MAP.get(col["id"], col["id"])
            row[label] = col["text"] or ""
        rows.append(row)

    df = pd.DataFrame(rows)
    if "Time Spent (minutes)" in df.columns:
        df["Time Spent (minutes)"] = pd.to_numeric(df["Time Spent (minutes)"], errors="coerce").fillna(0)
    else:
        df["Time Spent (minutes)"] = 0
    return df

def top_priority(priorities):
    ranked = [PRIORITY_ORDER.get(p, 99) for p in priorities]
    best = min(ranked)
    return next((k for k, v in PRIORITY_ORDER.items() if v == best), "")

def main():
    st.title("🎯 Customer Support Dashboard")
    st.caption(f"Last refresh: {datetime.now().strftime('%H:%M:%S')}  •  Auto-refreshes every 60 seconds")

    with st.spinner("Loading data from Monday..."):
        df = fetch_monday_data()

    if df.empty:
        st.warning("No data found on this board.")
        return

    total = len(df)
    resolved = len(df[df.get("Status", pd.Series(dtype=str)).str.strip() == "Resolved"]) if "Status" in df.columns else 0
    waiting = len(df[df["Status"].str.lower().str.contains("wait", na=False)]) if "Status" in df.columns else 0
    open_t = len(df[df["Status"].str.strip() == "Open"]) if "Status" in df.columns else 0
    avg_time = int(df["Time Spent (minutes)"].mean()) if total else 0

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("📋 Total Tickets", total)
    c2.metric("✅ Resolved", resolved)
    c3.metric("⏳ Waiting on Customer", waiting)
    c4.metric("🔴 Open", open_t)
    c5.metric("⏱ Avg Support Time", f"{avg_time} min")

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Issue Type")
        if "Issue Type" in df.columns:
            counts = df["Issue Type"].value_counts().reset_index()
            counts.columns = ["Issue Type", "Count"]
            fig = px.pie(counts, names="Issue Type", values="Count", hole=0.4, color_discrete_sequence=px.colors.qualitative.Set2)
            fig.update_layout(showlegend=True, margin=dict(t=10, b=10), height=280)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Resolution Type")
        if "Resolution Type" in df.columns:
            counts = df["Resolution Type"].value_counts().reset_index()
            counts.columns = ["Resolution Type", "Count"]
            fig = px.pie(counts, names="Resolution Type", values="Count", hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
            fig.update_layout(showlegend=True, margin=dict(t=10, b=10), height=280)
            st.plotly_chart(fig, use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        st.subheader("Customer Issue Verified")
        if "Customer Issue Verified" in df.columns:
            counts = df["Customer Issue Verified"].value_counts().reset_index()
            counts.columns = ["Verified", "Count"]
            fig = px.pie(counts, names="Verified", values="Count", hole=0.4, color="Verified", color_discrete_map={"Yes": "#639922", "No": "#E24B4A"})
            fig.update_layout(showlegend=True, margin=dict(t=10, b=10), height=280)
            st.plotly_chart(fig, use_container_width=True)

    with col4:
        st.subheader("Issue Source")
        if "Issue Source" in df.columns:
            counts = df["Issue Source"].value_counts().reset_index()
            counts.columns = ["Source", "Count"]
            fig = px.pie(counts, names="Source", values="Count", hole=0.4, color_discrete_sequence=px.colors.qualitative.Bold)
            fig.update_layout(showlegend=True, margin=dict(t=10, b=10), height=280)
            st.plotly_chart(fig, use_container_width=True)

    st.subheader("Tickets by Customer — sorted by highest priority")
    if "Customer" in df.columns and "Priority" in df.columns:
        cust_data = df.groupby("Customer").agg(Count=("Name", "count"), Priorities=("Priority", list)).reset_index()
        cust_data["Top Priority"] = cust_data["Priorities"].apply(top_priority)
        cust_data["Priority Rank"] = cust_data["Top Priority"].map(lambda p: PRIORITY_ORDER.get(p, 99))
        cust_data["Color"] = cust_data["Top Priority"].map(lambda p: PRIORITY_COLORS.get(p, "#888780"))
        cust_data = cust_data.sort_values("Priority Rank")

        fig = go.Figure(go.Bar(
            x=cust_data["Count"],
            y=cust_data["Customer"],
            orientation="h",
            marker_color=cust_data["Color"],
            text=cust_data["Top Priority"],
            textposition="auto",
        ))
        fig.update_layout(height=max(200, len(cust_data) * 50 + 80), margin=dict(t=10, b=10), xaxis=dict(title="Tickets", dtick=1), yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig, use_container_width=True)

    st.divider()
    if st.button("🔄 Refresh now"):
        st.cache_data.clear()
        st.rerun()

    time.sleep(60)
    st.rerun()

if __name__ == "__main__":
    main()
