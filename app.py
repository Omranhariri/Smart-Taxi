import streamlit as st
import pandas as pd
import plotly.express as px
import re
from supabase import create_client
from collections import Counter
from datetime import date

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Taxi Chatbot Dashboard",
    page_icon="🚖",
    layout="wide"
)

st.title("Smartcab Chatbot Analytics Dashboard")
st.markdown("Real-time insights from WhatsApp bookings.")
st.divider()

# ─────────────────────────────────────────────
# SUPABASE CONNECTION
# ─────────────────────────────────────────────
SUPABASE_URL = "https://pmhiigiiwiemgtjyuygg.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBtaGlpZ2lpd2llbWd0anl1eWdnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzEzNTQyNjgsImV4cCI6MjA4NjkzMDI2OH0.5dL0PzbcGhR-rKxsIlo4z62QqZfIbLfYsat8qhh_BbY"

@st.cache_resource
def get_client():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = get_client()

# ─────────────────────────────────────────────
# CONNECTION TEST
# ─────────────────────────────────────────────
#st.subheader("🔌 Connection Test")
#try:
#    test = supabase.table("sessions").select("session_id").limit(1).execute()
#    st.success("✅ Connected to Supabase successfully!")
#except Exception as e:
#    st.error(f"❌ Connection failed: {e}")

#st.divider()

# ─────────────────────────────────────────────
# FETCH DATA
# ─────────────────────────────────────────────
#@st.cache_data(ttl=5)
def fetch_sessions():
    response = supabase.table("sessions").select("*").execute()
    return pd.DataFrame(response.data)

#@st.cache_data(ttl=5)
def fetch_messages():
    response = supabase.table("messages").select("*").execute()
    return pd.DataFrame(response.data)

try:
    sessions_df = fetch_sessions()
    messages_df = fetch_messages()
except Exception as e:
    st.error(f"❌ Failed to fetch data: {e}")
    sessions_df = pd.DataFrame()
    messages_df = pd.DataFrame()

# ─────────────────────────────────────────────
# FILTERS SIDEBAR
# ─────────────────────────────────────────────
st.sidebar.header("🔧 Filters")

filtered_df = sessions_df.copy()

# ── Filter 1: Date Range ─────────────────────
st.sidebar.subheader("📅 Date Range")
if not sessions_df.empty and "created_at" in sessions_df.columns:
    sessions_df["created_at"] = pd.to_datetime(sessions_df["created_at"])
    min_date = sessions_df["created_at"].min().date()
    max_date = sessions_df["created_at"].max().date()
    start_date = st.sidebar.date_input("From", value=min_date, min_value=min_date, max_value=max_date)
    end_date = st.sidebar.date_input("To", value=max_date, min_value=min_date, max_value=max_date)
    filtered_df["created_at"] = pd.to_datetime(filtered_df["created_at"])
    filtered_df = filtered_df[
        (filtered_df["created_at"].dt.date >= start_date) &
        (filtered_df["created_at"].dt.date <= end_date)
    ]
else:
    st.sidebar.info("No date data available.")

# ── Filter 2: Status ─────────────────────────
st.sidebar.subheader("📋 Booking Status")
if not sessions_df.empty and "status" in sessions_df.columns:
    all_statuses = sessions_df["status"].dropna().unique().tolist()
    selected_statuses = st.sidebar.multiselect("Select status:", options=all_statuses, default=all_statuses)
    if selected_statuses:
        filtered_df = filtered_df[filtered_df["status"].isin(selected_statuses)]
else:
    st.sidebar.info("No status data available.")

# ── Filter 3: Confidence Score Range ────────
st.sidebar.subheader("🎯 Confidence Score")
if not sessions_df.empty and "confidence" in sessions_df.columns:
    confidence_level = st.sidebar.radio(
        "Select confidence level:",
        options=["All", "Low (0 - 0.4)", "Medium (0.4 - 0.7)", "High (0.7 - 1.0)"]
    )
    if confidence_level == "Low (0 - 0.4)":
        filtered_df = filtered_df[filtered_df["confidence"] < 0.4]
    elif confidence_level == "Medium (0.4 - 0.7)":
        filtered_df = filtered_df[(filtered_df["confidence"] >= 0.4) & (filtered_df["confidence"] < 0.7)]
    elif confidence_level == "High (0.7 - 1.0)":
        filtered_df = filtered_df[filtered_df["confidence"] >= 0.7]
else:
    st.sidebar.info("No confidence data available.")

st.sidebar.divider()
st.sidebar.markdown(f"**Showing {len(filtered_df)} of {len(sessions_df)} sessions**")

# ── Manual Refresh Button ────────
if st.sidebar.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()

# ─────────────────────────────────────────────
# HELPER: bar chart with labels
# ─────────────────────────────────────────────
def labeled_bar(df, x, y, orientation="h", color_scale="Blues"):
    fig = px.bar(
        df, x=x, y=y,
        orientation=orientation,
        color=x if orientation == "h" else y,
        color_continuous_scale=color_scale,
        text=x if orientation == "h" else y
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(
        yaxis={"categoryorder": "total ascending"} if orientation == "h" else {},
        coloraxis_showscale=False,
        xaxis_title=None,
        yaxis_title=None,
        margin=dict(l=0, r=40, t=10, b=0)
    )
    return fig

# ─────────────────────────────────────────────
# KPI METRICS
# ─────────────────────────────────────────────
col1, col2, col3 = st.columns(3)

total_bookings = len(filtered_df) if not filtered_df.empty else "N/A"

filtered_session_ids = filtered_df["session_id"].tolist() if not filtered_df.empty else []

if not messages_df.empty and "session_id" in messages_df.columns:
    filtered_messages = messages_df[messages_df["session_id"].isin(filtered_session_ids)]
    msg_counts = filtered_messages.groupby("session_id").size()
    avg_messages = round(msg_counts.mean(), 1) if not msg_counts.empty else "N/A"
else:
    avg_messages = "N/A"
    filtered_messages = pd.DataFrame()

if not filtered_df.empty and "confidence" in filtered_df.columns:
    avg_confidence = round(filtered_df["confidence"].dropna().mean(), 2)
else:
    avg_confidence = "N/A"

with col1:
    st.markdown(f"""
        <div style='text-align: center; padding: 20px; background-color: #1e1e1e; border-radius: 10px;'>
            <p style='color: grey; margin: 0; font-size: 14px;'>📋 Total Bookings</p>
            <h2 style='margin: 5px 0; color: white;'>{total_bookings}</h2>
        </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
        <div style='text-align: center; padding: 20px; background-color: #1e1e1e; border-radius: 10px;'>
            <p style='color: grey; margin: 0; font-size: 14px;'>💬 Avg Messages / Booking</p>
            <h2 style='margin: 5px 0; color: white;'>{avg_messages}</h2>
        </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
        <div style='text-align: center; padding: 20px; background-color: #1e1e1e; border-radius: 10px;'>
            <p style='color: grey; margin: 0; font-size: 14px;'>🎯 Avg Confidence Score</p>
            <h2 style='margin: 5px 0; color: white;'>{avg_confidence}</h2>
        </div>
    """, unsafe_allow_html=True)

st.divider()

# ─────────────────────────────────────────────
# CHARTS ROW 1: Status + Language
# ─────────────────────────────────────────────
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("📊 Bookings by Status")
    if not filtered_df.empty and "status" in filtered_df.columns:
        status_counts = filtered_df["status"].value_counts().reset_index()
        status_counts.columns = ["Status", "Count"]
        fig = px.bar(status_counts, x="Status", y="Count", text="Count", color="Count", color_continuous_scale="Blues")
        fig.update_traces(textposition="outside", cliponaxis=False)
        fig.update_layout(coloraxis_showscale=False, margin=dict(t=10, b=0), xaxis_title=None, yaxis_title=None)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No booking status data found.")

with col_right:
    st.subheader("🌍 Language Distribution")
    if not filtered_df.empty and "language" in filtered_df.columns:
        lang_counts = filtered_df["language"].value_counts().reset_index()
        lang_counts.columns = ["Language", "Count"]
        fig = px.bar(lang_counts, x="Language", y="Count", text="Count", color="Count", color_continuous_scale="Purples")
        fig.update_traces(textposition="outside", cliponaxis=False)
        fig.update_layout(coloraxis_showscale=False, margin=dict(t=10, b=0), xaxis_title=None, yaxis_title=None)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No language data found.")

st.divider()

# ─────────────────────────────────────────────
# TOP PICKUP & DROPOFF LOCATIONS
# ─────────────────────────────────────────────
st.subheader("📍 Top Pickup & Dropoff Locations")

col_pickup, col_dropoff = st.columns(2)

with col_pickup:
    st.markdown("**🟢 Top Pickup Locations**")
    if not filtered_df.empty and "pickup_location" in filtered_df.columns:
        pickup_counts = filtered_df["pickup_location"].dropna().value_counts().head(10).reset_index()
        pickup_counts.columns = ["Location", "Count"]
        st.plotly_chart(labeled_bar(pickup_counts, "Count", "Location", color_scale="Blues"), use_container_width=True)
    else:
        st.warning("No pickup location data found.")

with col_dropoff:
    st.markdown("**🔴 Top Dropoff Locations**")
    if not filtered_df.empty and "dropoff_location" in filtered_df.columns:
        dropoff_counts = filtered_df["dropoff_location"].dropna().value_counts().head(10).reset_index()
        dropoff_counts.columns = ["Location", "Count"]
        st.plotly_chart(labeled_bar(dropoff_counts, "Count", "Location", color_scale="Reds"), use_container_width=True)
    else:
        st.warning("No dropoff location data found.")

st.divider()

# ─────────────────────────────────────────────
# MISSING FIELDS + CUSTOMER LEADERBOARD (side by side)
# ─────────────────────────────────────────────
col_missing, col_leader = st.columns(2)

# ── Missing Fields ───────────────────────────
with col_missing:
    st.subheader("⚠️ Most Common Missing Fields")
    all_fields = []
    if not messages_df.empty and "missing_fields" in messages_df.columns:
        for val in filtered_messages["missing_fields"].dropna():
            if val:
                cleaned = re.sub(r"[\[\]\"\'']", "", str(val))
                all_fields.extend([f.strip() for f in cleaned.split(",") if f.strip()])

    if all_fields:
        field_counts = Counter(all_fields)
        field_df = pd.DataFrame(field_counts.items(), columns=["Field", "Count"]).sort_values("Count", ascending=False).reset_index(drop=True)
        field_df.index = field_df.index + 1
        st.dataframe(field_df, use_container_width=True)
    else:
        st.success("✅ No missing fields detected")

# ── Customer Leaderboard ─────────────────────
@st.cache_data(ttl=60)
def fetch_bookings():
    response = supabase.table("bookings").select("*").execute()
    return pd.DataFrame(response.data)

bookings_df = fetch_bookings()

with col_leader:
    st.subheader("🏆 Most Frequent Bookers")
    if not bookings_df.empty and "customer_name" in bookings_df.columns:
        leaderboard = bookings_df["customer_name"].dropna().value_counts().head(10).reset_index()
        leaderboard.columns = ["Customer Name", "Bookings"]
        leaderboard.index = leaderboard.index + 1
        st.dataframe(leaderboard, use_container_width=True)
    else:
        st.info("No customer name data available.")

st.divider()

# ─────────────────────────────────────────────
# RECENT BOOKINGS TABLE
# ─────────────────────────────────────────────
st.subheader("📋 Recent Bookings")
if not filtered_df.empty:
    cols_to_show = [c for c in ["session_id", "customer_name", "status", "pickup_location", "dropoff_location", "time", "language", "confidence", "created_at"] if c in filtered_df.columns]
    recent_df = filtered_df[cols_to_show].sort_values("created_at", ascending=False).head(10) if "created_at" in filtered_df.columns else filtered_df[cols_to_show].head(10)
    st.dataframe(recent_df, use_container_width=True)
else:
    st.info("No bookings match the selected filters.")

st.caption("Data refreshes every 60 seconds. Use the sidebar to filter results.")

