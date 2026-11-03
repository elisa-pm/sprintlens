"""SprintLens dashboard. Run with: streamlit run app/streamlit_app.py"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sprintlens import metrics as m  # noqa: E402
from sprintlens import retro_analyzer as ra  # noqa: E402

BLUE, GREY, ORANGE = "#2F6FDE", "#9AA5B1", "#E8833A"

st.set_page_config(page_title="SprintLens", layout="wide")
st.title("SprintLens")
st.caption("Sprint health and retrospective insights. All bundled data is synthetic.")

# ---------------------------------------------------------------- data
with st.sidebar:
    st.header("Data")
    up_s = st.file_uploader("sprints.csv", type="csv")
    up_i = st.file_uploader("issues.csv", type="csv")
    st.caption("Leave empty to use the synthetic sample. Schema: docs/metric_definitions.md")


@st.cache_data
def load_data(sprints_file, issues_file):
    if sprints_file is not None and issues_file is not None:
        s = pd.read_csv(sprints_file, parse_dates=m.DATE_COLS_SPRINTS)
        i = pd.read_csv(issues_file, parse_dates=m.DATE_COLS_ISSUES)
        for col in ("carried_in", "added_mid_sprint"):
            i[col] = i[col].astype(bool)
        return s, i
    return m.load(str(ROOT / "data/sprints.csv"), str(ROOT / "data/issues.csv"))


sprints, issues = load_data(up_s, up_i)
summary = m.sprint_summary(sprints, issues)
kp = m.kpis(summary)

# ---------------------------------------------------------------- KPIs
c1, c2, c3, c4 = st.columns(4)
c1.metric("Velocity (last 3 sprints)", f"{kp['velocity_recent']:.0f} pts", f"{kp['velocity_change_pct']:+.0f}% vs first 3")
c2.metric("Completion rate", f"{kp['completion_recent']:.0%}")
c3.metric("Carryover rate", f"{kp['carryover_recent']:.0%}")
c4.metric("Cycle time p85", f"{kp['p85_cycle_recent']:.1f} days")

tab_vel, tab_burn, tab_flow, tab_fc, tab_retro = st.tabs(
    ["Velocity", "Burndown", "Flow", "Forecast", "Retro insights"]
)

# ---------------------------------------------------------------- velocity
with tab_vel:
    fig = go.Figure()
    fig.add_bar(x=summary.name, y=summary.committed_pts + summary.added_pts, name="Planned", marker_color=GREY)
    fig.add_bar(x=summary.name, y=summary.completed_pts, name="Completed", marker_color=BLUE)
    fig.add_scatter(x=summary.name, y=summary.velocity_3sprint_avg, name="3-sprint average", mode="lines+markers", line=dict(color=ORANGE, width=3))
    fig.update_layout(barmode="group", yaxis_title="Story points", legend_orientation="h", margin=dict(t=20))
    st.plotly_chart(fig, use_container_width=True)
    rate = px.line(summary, x="name", y=["completion_rate", "carryover_rate"], markers=True)
    rate.update_layout(yaxis_tickformat=".0%", yaxis_title="Share of planned points", xaxis_title=None, legend_title=None, margin=dict(t=20))
    st.plotly_chart(rate, use_container_width=True)

# ---------------------------------------------------------------- burndown
with tab_burn:
    sid = st.selectbox("Sprint", summary.sprint_id.tolist(), index=len(summary) - 1)
    bd = m.burndown(sprints, issues, sid)
    fig = go.Figure()
    fig.add_scatter(x=bd.date, y=bd.ideal, name="Ideal", line=dict(color=GREY, dash="dash"))
    fig.add_scatter(x=bd.date, y=bd.remaining, name="Remaining", line=dict(color=BLUE, width=3), line_shape="hv")
    fig.update_layout(yaxis_title="Remaining points", legend_orientation="h", margin=dict(t=20))
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Mid-sprint additions raise the remaining line on the day they start.")

# ---------------------------------------------------------------- flow
with tab_flow:
    left, right = st.columns(2)
    ct = m.cycle_times(issues)
    ct["sprint"] = "S" + ct.sprint_id.astype(str)
    scatter = px.box(ct, x="sprint", y="cycle_days", points="all", color_discrete_sequence=[BLUE])
    scatter.update_layout(yaxis_title="Cycle time (days)", xaxis_title=None, margin=dict(t=30), title="Cycle time by sprint")
    left.plotly_chart(scatter, use_container_width=True)
    wip = m.wip_daily(sprints, issues, sid)
    area = px.area(wip, x="date", y="wip", color_discrete_sequence=[ORANGE])
    area.update_layout(yaxis_title="Items in progress", xaxis_title=None, margin=dict(t=30), title="Work in progress (sprint chosen on Burndown tab)")
    right.plotly_chart(area, use_container_width=True)

# ---------------------------------------------------------------- forecast
with tab_fc:
    st.write("Monte Carlo forecast: how many sprints to finish the remaining backlog, sampling from recent velocity.")
    a, b = st.columns(2)
    remaining = a.number_input("Remaining backlog (points)", min_value=1, value=150, step=10)
    window = b.slider("Sprints of history to sample", 3, len(summary), min(6, len(summary)))
    res = m.forecast_sprints(summary.completed_pts.tail(window).tolist(), remaining)
    x, y, z = st.columns(3)
    x.metric("50% confidence", f"{res['p50']} sprints")
    y.metric("85% confidence", f"{res['p85']} sprints")
    z.metric("95% confidence", f"{res['p95']} sprints")
    st.caption("Forecasts describe the past pattern of delivery. They are ranges, not commitments.")

# ---------------------------------------------------------------- retro
with tab_retro:
    retro_dir = ROOT / "data/retros"
    items = ra.classify_offline(ra.load_retros(retro_dir)) if retro_dir.exists() else []
    if not items:
        st.info("No retrospective notes found in data/retros.")
    else:
        df = ra.to_frame(items)
        matrix = ra.theme_matrix(df, "improve")
        heat = px.imshow(
            matrix, aspect="auto", color_continuous_scale="Blues",
            labels=dict(x="Sprint", y="Theme", color="Mentions"),
        )
        heat.update_layout(margin=dict(t=20), title="What did not go well: themes by sprint")
        st.plotly_chart(heat, use_container_width=True)
        st.markdown(ra.build_report(items))
