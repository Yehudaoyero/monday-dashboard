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
        columns { id title }
        items_page(limit: 500) {
          items {
            name
            column_values { id text }
          }
        }
      }
    }
    """ % BOARD_ID)

    if not data:
        return pd.DataFrame()

    board = data["data"]["boards"][0]
    columns = {col["id"]: col["title"] for col in board["columns"]}
    items = board["items_page"]["items"]

    rows = []
    for item in items:
        row = {"Name": item["name"]}
        for col in item["column_values"]:
            title = columns.get(col["id"], col["id"])
            row[title] = col.get("text") or ""
        rows.append(row)

    df = pd.DataFrame(rows)
    time_col = "Time Spent (minutes)"
    if time_col in df.columns:
        df[time_col] = pd.to_numeric(df[time_col], errors="coerce").fillna(0)
    else:
        df[time_col] = 0
    return df

def main():
    st.markdown(
        f"""
        <div style="display:flex; align-items:center; gap:16px; margin-bottom:8px;">
            <img src="https://raw.githubusercontent.com/Yehudaoyero/monday-dashboard/main/Logo.png" height="120" style="margin-top:-30px;">
            <div>
                <div style="font-size:28px; font-weight:700; color: var(--text-color);">Customer Support Dashboard</div>
                <div style="font-size:13px; color:gray;">Last refresh: {datetime.now().strftime('%H:%M:%S')} • Auto-refreshes every 60 seconds</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

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

    def make_pie(title, data_col, color_map=None, colors=None):
        if data_col not in df.columns:
            return
        counts = df[df[data_col] != ""][data_col].value_counts().reset_index()
        counts.columns = [data_col, "Count"]
        if color_map:
            fig = px.pie(counts, names=data_col, values="Count", hole=0.45,
                         color=data_col, color_discrete_map=color_map,
                         title=title)
        else:
            fig = px.pie(counts, names=data_col, values="Count", hole=0.45,
                         color_discrete_sequence=colors or px.colors.qualitative.Set2,
                         title=title)
        fig.update_layout(
            title=dict(text=title, x=0.5, xanchor="center", font=dict(size=16)),
            showlegend=True,
            legend=dict(orientation="h", yanchor="top", y=-0.05, xanchor="center", x=0.5),
            margin=dict(t=50, b=60, l=10, r=10),
            height=300
        )
        fig.update_traces(textposition="inside", textinfo="percent")
        st.plotly_chart(fig, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        make_pie("Issue Type", "Issue Type", colors=px.colors.qualitative.Set2)
    with col2:
        make_pie("Resolution Type", "Resolution Type", colors=px.colors.qualitative.Pastel)

    col3, col4 = st.columns(2)
    with col3:
        make_pie("Customer Issue Verified", "Customer Issue Verified", color_map={"Yes": "#639922", "No": "#E24B4A"})
    with col4:
        make_pie("Issue Source", "Issue Source", colors=px.colors.qualitative.Bold)

    st.subheader("Tickets by Customer — sorted by volume")
    if customer_col in df.columns:
        df_cust = df[df[customer_col].str.strip() != ""]
        if not df_cust.empty:
            cust_data = df_cust[customer_col].value_counts().reset_index()
            cust_data.columns = ["Customer", "Count"]
            cust_data = cust_data.sort_values("Count", ascending=True)
            # Add prefix to prevent numeric customer names from being treated as numbers
            cust_data["CustomerLabel"] = cust_data["Customer"].apply(lambda x: f"  {x}")
            fig = go.Figure(go.Bar(
                x=cust_data["Count"],
                y=cust_data["CustomerLabel"],
                orientation="h",
                marker_color="#378ADD",
                text=cust_data["Count"],
                textposition="auto",
            ))
            fig.update_layout(
                height=max(200, len(cust_data) * 50 + 80),
                margin=dict(t=10, b=10),
                xaxis=dict(title="Tickets", dtick=1),
                yaxis=dict(type="category"),
            )
            st.plotly_chart(fig, use_container_width=True)

    st.divider()
    if st.button("🔄 Refresh now"):
        st.cache_data.clear()
        st.rerun()

    time.sleep(60)
    st.rerun()

if __name__ == "__main__":
    main()
