"""Estadísticas y gráficas personales del empleado."""

from __future__ import annotations

from datetime import timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from .. import analytics, auth, db, theme
from ..config import COLORS, STATUS_COLORS, STATUS_LABELS
from ..tz import minutes_to_hhmm, today_gt
from .history import _range_picker

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color=COLORS["text"], size=12),
    margin=dict(l=10, r=10, t=40, b=10),
    xaxis=dict(gridcolor=COLORS["border"], zerolinecolor=COLORS["border"]),
    yaxis=dict(gridcolor=COLORS["border"], zerolinecolor=COLORS["border"]),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
)


def weekly_chart(grid: pd.DataFrame) -> go.Figure:
    df = grid.copy()
    df["semana"] = df["fecha"].apply(lambda d: (d - timedelta(days=d.isoweekday() - 1)))
    agg = df.groupby("semana", as_index=False).agg(
        trabajadas=("neto_min", "sum"),
        esperadas=("esperado_min", "sum"),
    )
    agg["trabajadas"] = (agg["trabajadas"] / 60).round(2)
    agg["esperadas"] = (agg["esperadas"] / 60).round(2)
    agg["etiqueta"] = agg["semana"].apply(lambda d: f"Sem. {d.strftime('%d/%m')}")

    fig = go.Figure()
    fig.add_bar(x=agg["etiqueta"], y=agg["trabajadas"], name="Trabajadas",
                marker_color=COLORS["primary"])
    fig.add_trace(go.Scatter(x=agg["etiqueta"], y=agg["esperadas"], name="Esperadas",
                             mode="lines+markers", line=dict(color=COLORS["muted"], dash="dot")))
    fig.update_layout(title="Horas por semana", **PLOTLY_LAYOUT)
    return fig


def status_pie(grid: pd.DataFrame) -> go.Figure:
    counted = grid[grid["laboral"] & (grid["estado"] != "future")]
    counts = counted["estado"].value_counts()
    labels = [STATUS_LABELS.get(k, k) for k in counts.index]
    colors = [STATUS_COLORS.get(k, COLORS["muted"]) for k in counts.index]
    fig = go.Figure(go.Pie(labels=labels, values=counts.values, hole=0.55,
                           marker=dict(colors=colors), textinfo="label+percent"))
    fig.update_layout(title="Distribución de días", showlegend=False, **{
        k: v for k, v in PLOTLY_LAYOUT.items() if k not in ("xaxis", "yaxis")
    })
    return fig


def punctuality_chart(grid: pd.DataFrame) -> go.Figure:
    df = grid[grid["entrada"].notna()].copy()
    if df.empty:
        return go.Figure()
    df["minutos"] = df["tarde_min"]
    fig = go.Figure()
    fig.add_bar(
        x=df["fecha"], y=df["minutos"],
        marker_color=[COLORS["success"] if m <= 0 else
                      (COLORS["warning"] if m <= 15 else COLORS["danger"])
                      for m in df["minutos"]],
        name="Minutos respecto a la hora de entrada",
    )
    fig.add_hline(y=15, line_dash="dot", line_color=COLORS["muted"],
                  annotation_text="Tolerancia", annotation_position="top left")
    fig.update_layout(title="Puntualidad diaria (minutos de retraso)", **PLOTLY_LAYOUT)
    return fig


def render() -> None:
    profile = auth.current_profile()
    user_id = auth.current_user_id()
    start, end = _range_picker("stats")

    attendance = db.fetch_attendance(start, end, employee_id=user_id)
    exceptions = db.fetch_exceptions(start, end, employee_id=user_id)
    holidays = db.fetch_holidays(start, end)
    grid = analytics.build_grid([profile], attendance, exceptions, holidays, start, end)

    if grid.empty:
        st.info("No hay información en el período seleccionado.")
        return

    laborales = grid[grid["laboral"] & (grid["estado"] != "future")]
    dias_trabajados = int((grid["neto_min"] > 0).sum())
    promedio = grid.loc[grid["neto_min"] > 0, "neto_min"].mean() if dias_trabajados else 0
    puntualidad = (
        100 * (grid["estado"] == "on_time").sum() / len(laborales) if len(laborales) else 0
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(theme.stat("Días trabajados", str(dias_trabajados)), unsafe_allow_html=True)
    c2.markdown(theme.stat("Promedio diario", minutes_to_hhmm(promedio)), unsafe_allow_html=True)
    c3.markdown(
        theme.stat("Puntualidad", f"{puntualidad:.0f}%",
                   color=COLORS["success"] if puntualidad >= 80 else COLORS["warning"]),
        unsafe_allow_html=True,
    )
    c4.markdown(
        theme.stat("Horas extra", minutes_to_hhmm(grid["extra_min"].sum())),
        unsafe_allow_html=True,
    )

    st.write("")
    st.plotly_chart(weekly_chart(grid), width="stretch")

    left, right = st.columns([1.3, 1])
    with left:
        st.plotly_chart(punctuality_chart(grid), width="stretch")
    with right:
        st.plotly_chart(status_pie(grid), width="stretch")
