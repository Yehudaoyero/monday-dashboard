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

def gql(query):
    r = requests.post(
        "https://api.monday.com/v2",
        json={"query": query},
        headers={"Authorization": API_TOKEN, "Content-Type": "application/json", "API-Version": "2024-01"}
    )
    data = r.json()
    if "errors" in data:
        st.error(f"API Error: {data['errors']}")
        return None
    return data

@st.cache_data(ttl=60)
def fetch_monday_data():
    data = gql("""
    {
      boards(ids: %s) {
        columns { id title settings_str }
        items_page(limit: 500) {
          items {
            name
            column_values { id text value }
          }
        }
      }
    }
    """ % BOARD_ID)

    if not data:
        return pd.DataFrame()

    board = data["data"]["boards"][0]

    # Build label maps for dropdown columns
    dropdown_labels = {}
    columns = {}
    for col in board["columns"]:
        columns[col["id"]] = col["title"]
        try:
            settings = json.loads(col.get("settings_str") or "{}")
            labels = settings.get("labels", [])
            if labels:
                # labels is a list of {id, name} or dict {id: name}
                if isinstance(labels, list):
                    dropdown_labels[col["id"]] = {str(l["id"]): l["name"] for l in labels if "id" in l and "name" in l}
                elif isinstance(labels, dict):
                    dropdown_labels[col["id"]] = {str(k): v for k, v in labels.items()}
        except:
            pass

    items = board["items_page"]["items"]

    rows = []
    for item in items:
        row = {"Name": item["name"]}
        for col in item["column_values"]:
            col_id = col["id"]
            title = columns.get(col_id, col_id)
            text = col.get("text") or ""

            # If text looks like a number and we have dropdown labels — map it
            if col_id in dropdown_labels and text:
                label_map = dropdown_labels[col_id]
                # text might be comma-separated IDs
                parts = [p.strip() for p in text.split(",")]
                mapped = [label_map.get(p, p) for p in parts if p]
                if mapped:
                    text = ", ".join(mapped)

            row[title] = text
        rows.append(row)

    df = pd.DataFrame(rows)
    time_col = "Time Spent (minutes)"
    if time_col in df.columns:
        df[time_col] = pd.to_numeric(df[time_col], errors="coerce").fillna(0)
    else:
        df[time_col] = 0
    return df

def main():
    st.title("🎯 Customer Support Dashboard")
    st.caption(f"Last refresh: {datetime.now().strftime('%H:%M:%S')}  •  Auto-refreshes every 60 seconds")

    with st.spinner("Loading data from Monday..."):
        df = fetch_monday_data()

    if df.empty:
        st.warning("No data found on this board.")
        return

    status_col = "Status"
    time_col = "Time Spent (minutes)"
    customer_col = "Customer"

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

    st.subheader("Tickets by Customer — sorted by volume")
    if customer_col in df.columns:
        df_cust = df[df[customer_col].str.strip() != ""]
        if not df_cust.empty:
            cust_data = df_cust[customer_col].value_counts().reset_index()
            cust_data.columns = ["Customer", "Count"]
            cust_data = cust_data.sort_values("Count", ascending=True)
            fig = go.Figure(go.Bar(
                x=cust_data["Count"],
                y=cust_data["Customer"],
                orientation="h",
                marker_color="#378ADD",
                text=cust_data["Count"],
                textposition="auto",
            ))
            fig.update_layout(
                height=max(200, len(cust_data) * 50 + 80),
                margin=dict(t=10, b=10),
                xaxis=dict(title="Tickets", dtick=1),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"Customer values: {df[customer_col].unique().tolist()}")

    st.divider()
    if st.button("🔄 Refresh now"):
        st.cache_data.clear()
        st.rerun()

    time.sleep(60)
    st.rerun()

if __name__ == "__main__":
    main()
