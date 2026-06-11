import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import time
import json

st.set_page_config(page_title="Customer Support Dashboard", page_icon="🎯", layout="wide")

API_TOKEN = st.secrets["MONDAY_API_TOKEN"]
BOARD_ID = st.secrets.get("MONDAY_BOARD_ID", "5098274792")

PRIORITY_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
PRIORITY_COLORS = {"Critical": "#A32D2D", "High": "#E24B4A", "Medium": "#EF9F27", "Low": "#639922"}

def gql(query):
    r = requests.post(
        "https://api.monday.com/v2",
        json={"query": query},
        headers={"Authorization": API_TOKEN, "Content-Type": "application/json", "API-Version": "2024-01"}
    )
    return r.json()

@st.cache_data(ttl=60)
def fetch_monday_data():
    data = gql("""
    {
      boards(ids: %s) {
        columns { id title }
        items_page(limit: 500) {
          items {
            name
            column_values { id text value }
          }
        }
      }
    }
    """ % BOARD_ID)

    board = data["data"]["boards"][0]
    columns = {col["id"]: col["title"] for col in board["columns"]}
    items = board["items_page"]["items"]

    rows = []
    for item in items:
        row = {"Name": item["name"]}
        for col in item["column_values"]:
            title = columns.get(col["id"], col["id"])
            text = col.get("text") or ""
            if not text and col.get("value"):
                try:
                    val = json.loads(col["value"])
                    if isinstance(val, dict):
                        text = val.get("display_value") or val.get("text") or val.get("name") or ""
                    elif isinstance(val, list) and val:
                        text = str(val[0])
                except:
                    pass
            row[title] = text
        rows.append(row)

    df = pd.DataFrame(rows)
    time_col = "Time Spent (minutes)"
    if time_col in df.columns:
        df[time_col] = pd.to_numeric(df[time_col], errors="coerce").fillna(0)
    else:
        df[time_col] = 0
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

    status_col = "Status"
    customer_col = "Customer"
    time_col = "Time Spent (minutes)"

    total = len(df)
    resolved = len(df[df[status_col].str.strip() == "Resolved"]) if status_col in df.columns else 0
    waiting = len(df[df[status_col].str.lower().str.contains("wait", na=False)]) if status_col in df.columns else 0
    open_t = len(df[df[status_col].str.strip() == "Open"]) if status_col in df.columns else 0
    avg_time = int(df[time_col].mean()) if total and time_col in df.columns else 0

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
    if customer_col in df.columns and "Priority" in df.columns:
        df_cust = df[df[customer_col].str.strip() != ""]
        if not df_cust.empty:
            cust_data = df_cust.groupby(customer_col).agg(Count=("Name", "count"), Priorities=("Priority", list)).reset_index()
            cust_data["Top Priority"] = cust_data["Priorities"].apply(top_priority)
            cust_data["Priority Rank"] = cust_data["Top Priority"].map(lambda p: PRIORITY_ORDER.get(p, 99))
            cust_data["Color"] = cust_data["Top Priority"].map(lambda p: PRIORITY_COLORS.get(p, "#888780"))
            cust_data = cust_data.sort_values("Priority Rank")
            fig = go.Figure(go.Bar(
                x=cust_data["Count"],
                y=cust_data[customer_col],
                orientation="h",
                marker_color=cust_data["Color"],
                text=cust_data["Top Priority"],
                textposition="auto",
            ))
            fig.update_layout(height=max(200, len(cust_data) * 50 + 80), margin=dict(t=10, b=10), xaxis=dict(title="Tickets", dtick=1), yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No customer data available")

    st.divider()
    if st.button("🔄 Refresh now"):
        st.cache_data.clear()
        st.rerun()

    time.sleep(60)
    st.rerun()

if __name__ == "__main__":
    main()
