"""
Daily Monitoring Dashboard — Streamlit app for the accounting team.
Connects directly to BigQuery. Run with: streamlit run dashboard/daily_monitoring.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, timedelta
import sys
sys.path.insert(0, "..")

from mcp_server.services.bigquery_client import BigQueryClient
from mcp_server.tools.staging import approve_transaction, reject_transaction

# ------------------------------------------------------------------ #
# Page config                                                          #
# ------------------------------------------------------------------ #
st.set_page_config(
    page_title="Carrier Accounting — Daily Monitor",
    page_icon="📊",
    layout="wide",
)

bq = BigQueryClient()

# ------------------------------------------------------------------ #
# Sidebar                                                              #
# ------------------------------------------------------------------ #
st.sidebar.title("⚙️ Controls")
target_date = st.sidebar.date_input("Date", value=date.today())
reviewer_name = st.sidebar.text_input("Reviewer Name", placeholder="Your name")
st.sidebar.markdown("---")
st.sidebar.markdown("**Mode Legend**")
st.sidebar.markdown("🔵 Trial — shadow writes only")
st.sidebar.markdown("🟢 Live — writing to Applied Epic")

# ------------------------------------------------------------------ #
# Header                                                               #
# ------------------------------------------------------------------ #
st.title("📊 Carrier Accounting — Daily Scorecard")
st.caption(f"Showing data for **{target_date.strftime('%B %d, %Y')}**")

# ------------------------------------------------------------------ #
# Daily Metrics                                                        #
# ------------------------------------------------------------------ #
metrics = bq.get_daily_metrics(target_date)

if not metrics or not metrics.get("total_transactions"):
    st.info(f"No runs found for {target_date}. Check back after the daily ingestion job runs.")
    st.stop()

total = metrics.get("total_transactions", 0)
auto_approved = metrics.get("auto_approved", 0)
review_queue = metrics.get("review_queue", 0)
posted = metrics.get("posted_to_epic", 0)
rejected = metrics.get("rejected", 0)
failed = metrics.get("failed", 0)
avg_conf = metrics.get("avg_confidence", 0) or 0
total_amount = metrics.get("total_amount", 0) or 0

auto_rate = (auto_approved / total * 100) if total > 0 else 0

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Transactions", f"{total:,}")
col2.metric("Auto-Approved", f"{auto_approved:,}", f"{auto_rate:.1f}%")
col3.metric("Review Queue", f"{review_queue:,}",
            delta=None if review_queue == 0 else f"⚠️ {review_queue} need review",
            delta_color="inverse")
col4.metric("Posted to Epic", f"{posted:,}")
col5.metric("Avg Confidence", f"{avg_conf:.1%}")

st.markdown("---")

# ------------------------------------------------------------------ #
# Trend Charts                                                         #
# ------------------------------------------------------------------ #
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("📈 7-Day Accuracy Trend")
    trend_data = []
    for i in range(7):
        d = target_date - timedelta(days=6 - i)
        m = bq.get_daily_metrics(d)
        if m and m.get("total_transactions"):
            t = m["total_transactions"]
            trend_data.append({
                "date": d,
                "auto_rate": (m.get("auto_approved", 0) / t * 100) if t > 0 else 0,
                "avg_confidence": (m.get("avg_confidence") or 0) * 100,
                "total": t,
            })

    if trend_data:
        df_trend = pd.DataFrame(trend_data)
        fig = px.line(df_trend, x="date", y=["auto_rate", "avg_confidence"],
                      labels={"value": "%", "variable": "Metric"},
                      color_discrete_map={"auto_rate": "#2ecc71", "avg_confidence": "#3498db"})
        fig.update_layout(height=300, showlegend=True, margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig, use_container_width=True)

with col_right:
    st.subheader("🥧 Today's Status Breakdown")
    status_data = {
        "Auto-Approved": auto_approved,
        "Review Queue": review_queue,
        "Rejected": rejected,
        "Failed": failed,
    }
    fig_pie = go.Figure(data=[go.Pie(
        labels=list(status_data.keys()),
        values=list(status_data.values()),
        hole=0.4,
        marker_colors=["#2ecc71", "#f39c12", "#e74c3c", "#95a5a6"],
    )])
    fig_pie.update_layout(height=300, margin=dict(l=0, r=0, t=30, b=0))
    st.plotly_chart(fig_pie, use_container_width=True)

st.markdown("---")

# ------------------------------------------------------------------ #
# Exception / Review Queue                                             #
# ------------------------------------------------------------------ #
st.subheader("⚠️ Exception Queue — Needs Human Review")

queue = bq.get_exception_queue(target_date)

if not queue:
    st.success("✅ No exceptions today — all transactions auto-approved!")
else:
    st.warning(f"{len(queue)} transactions need your review before they can be posted to Epic.")

    df_queue = pd.DataFrame(queue)
    display_cols = [
        "transaction_id", "carrier", "policy_number", "client_name",
        "amount", "confidence_score", "validation_errors", "validation_warnings"
    ]
    df_display = df_queue[[c for c in display_cols if c in df_queue.columns]]
    df_display["confidence_score"] = df_display["confidence_score"].apply(lambda x: f"{x:.1%}")

    st.dataframe(df_display, use_container_width=True, height=300)

    st.markdown("**Review Actions**")
    col_a, col_b = st.columns(2)

    with col_a:
        selected_id = st.text_input("Transaction ID to review")
        action = st.radio("Action", ["Approve", "Reject"], horizontal=True)
        notes = st.text_area("Notes / Reason")

        if st.button("Submit Review"):
            if not reviewer_name:
                st.error("Please enter your reviewer name in the sidebar.")
            elif not selected_id:
                st.error("Please enter a transaction ID.")
            else:
                if action == "Approve":
                    result = approve_transaction(selected_id, reviewer_name, notes)
                    st.success(f"✅ Approved: {selected_id}")
                else:
                    if not notes:
                        st.error("Rejection reason is required.")
                    else:
                        result = reject_transaction(selected_id, reviewer_name, notes)
                        st.success(f"❌ Rejected: {selected_id}")
                st.rerun()

    with col_b:
        st.markdown("**Bulk Actions**")
        run_id_bulk = st.text_input("Run ID for bulk approval")
        if st.button("✅ Approve Entire Run"):
            if not reviewer_name:
                st.error("Enter reviewer name in sidebar first.")
            elif not run_id_bulk:
                st.error("Enter a run ID.")
            else:
                from mcp_server.tools.staging import approve_batch
                result = approve_batch(run_id_bulk, reviewer_name)
                st.success(f"Approved {result['approved']} transactions in run {run_id_bulk}")
                st.rerun()

st.markdown("---")

# ------------------------------------------------------------------ #
# Amount Summary                                                       #
# ------------------------------------------------------------------ #
st.subheader("💰 Financial Summary")
col_f1, col_f2, col_f3 = st.columns(3)
col_f1.metric("Total Amount Processed", f"${total_amount:,.2f}")
col_f2.metric("Transactions Rejected", f"{rejected:,}")
col_f3.metric("Failed Epic Writes", f"{failed:,}",
              delta_color="inverse" if failed > 0 else "normal")

st.caption("Dashboard auto-refreshes — press R to reload. Data sourced from BigQuery.")
