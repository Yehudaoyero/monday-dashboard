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
def fetch_raw():
    return gql("""
    {
      boards(ids: %s) {
        columns { id title settings_str }
        items_page(limit: 5) {
          items {
            name
            column_values { id text value }
          }
        }
      }
    }
    """ % BOARD_ID)

def main():
    st.title("🔍 Debug — Raw API Data")

    data = fetch_raw()
    if not data:
        return

    board = data["data"]["boards"][0]

    st.subheader("Columns & Settings")
    for col in board["columns"]:
        if col["title"] in ("Customer", "Status", "Priority", "Issue Type"):
            st.write(f"**{col['title']}** (id: {col['id']})")
            try:
                settings = json.loads(col.get("settings_str") or "{}")
                st.json(settings)
            except:
                st.write("No settings")

    st.subheader("First 5 Items — Raw Values")
    for item in board["items_page"]["items"]:
        st.write(f"**{item['name']}**")
        for col in item["column_values"]:
            if col["id"] in [c["id"] for c in board["columns"] if c["title"] in ("Customer", "Status", "Priority")]:
                st.write(f"  - {col['id']}: text=`{col['text']}` value=`{col['value']}`")

if __name__ == "__main__":
    main()
