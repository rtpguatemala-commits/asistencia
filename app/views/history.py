"""Historial personal del empleado."""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st

from .. import analytics, auth, db, theme
from ..config import COLORS, STATUS_COLORS, STATUS_LABELS
from ..tz import (
    fmt_date,
    fmt_date_short,
    hhmm,
    minutes_to_hhmm,
    month_bounds,
    today_gt,
)


def _range_picker(key_prefix: str) -> tuple[date, date]:
    today = today_gt()
    first, last = month_bounds(today)
    presets = {
        "Este mes": (first, today),
        "Mes pasado": month_bounds(first - timedelta(days=1)),
        "Últimos 7 días": (today - timedelta(days=6), today),
        "Últimos 30 días": (today - timedelta(days=29), today),
        "Este año": (date(today.year, 1, 1), today),
        "Personalizado": None,
    }
    choice = st.selectbox("Período", list(presets.keys()), key=f"{key_prefix}_preset")
    if presets[choice] is None:
        cols = st.columns(2)
        start = cols[0].date_input("Desde", value=first, key=f"{key_prefix}_from", format="DD/MM/YYYY")
        end = cols[1].date_input("Hasta", value=today, key=f"{key_prefix}_to", format="DD/MM/YYYY")
    else:
        start, end = presets[choice]
    if start > end:
        start, end = end, start
    return start, end


def calendar_html(grid: pd.DataFrame, start: date, end: date) -> str:
    """Tira de días coloreada por estado."""
    if grid.empty:
        return ""
    cells = []
    for _, row in grid.iterrows():
        color = STATUS_COLORS.get(row["estado"], COLORS["border"])
        titulo = (f"{fmt_date_short(row['fecha'])} · {row['estado_texto']}"
                  f" · {minutes_to_hhmm(row['neto_min']) if row['neto_min'] else ''}")
        cells.append(
            f'<div title="{titulo}" style="width:26px;height:26px;border-radius:7px;'
            f'background:{color}33;border:1px solid {color}88;display:flex;'
            f'align-items:center;justify-content:center;font-size:.62rem;'
            f'color:{color};font-weight:700">{row["fecha"].day}</div>'
        )
    leyenda = " ".join(
        f'<span style="display:inline-flex;align-items:center;gap:.3rem;margin-right:.8rem;'
        f'font-size:.72rem;color:{COLORS["muted"]}">'
        f'<span style="width:.55rem;height:.55rem;border-radius:3px;background:{c}"></span>'
        f'{STATUS_LABELS[k]}</span>'
        for k, c in [("on_time", STATUS_COLORS["on_time"]),
                     ("late", STATUS_COLORS["late"]),
                     ("absent", STATUS_COLORS["absent"]),
                     ("exception", STATUS_COLORS["exception"]),
                     ("holiday", STATUS_COLORS["holiday"]),
                     ("rest", STATUS_COLORS["rest"])]
    )
    return (
        '<div style="display:flex;flex-wrap:wrap;gap:5px;margin:.4rem 0 .8rem">'
        + "".join(cells)
        + "</div>"
        + f'<div style="margin-bottom:.4rem">{leyenda}</div>'
    )


def detail_table(grid: pd.DataFrame) -> pd.DataFrame:
    view = pd.DataFrame({
        "Fecha": grid["fecha"].apply(fmt_date_short),
        "Día": grid["dia"],
        "Horario": grid["horario"],
        "Entrada": grid["entrada"].apply(hhmm),
        "Salida": grid["salida"].apply(hhmm),
        "Lugar": grid["modo_entrada"].map({"building": "Edificio", "other": "Otro lugar"}).fillna("—"),
        "Netas": grid["neto_min"].apply(lambda m: minutes_to_hhmm(m) if m else "—"),
        "Retraso": grid["tarde_min"].apply(lambda m: f"{int(m)} min" if m else "—"),
        "Estado": grid["estado_texto"],
        "Nota": grid.apply(
            lambda r: r["asueto"] or r["excepcion"] or r["observacion"] or "", axis=1
        ),
        "Tareas reportadas": grid.get("bitacora", ""),
    })
    return view


def _request_correction(profile: dict, grid: pd.DataFrame) -> None:
    st.markdown("Si algún día quedó mal registrado, pídele la corrección a la gerencia.")
    candidatos = grid[grid["estado"].isin(
        ["absent", "open", "late", "early_leave", "late_and_early", "on_time"]
    )]
    if candidatos.empty:
        st.caption("No hay días que corregir en el período mostrado.")
        return

    opciones = {
        f"{fmt_date_short(r['fecha'])} · {r['dia']} · {r['estado_texto']}": r["fecha"]
        for _, r in candidatos.sort_values("fecha", ascending=False).iterrows()
    }
    etiqueta = st.selectbox("Día a corregir", list(opciones.keys()), key="corr_day")
    dia = opciones[etiqueta]

    cols = st.columns(2)
    hora_in = cols[0].time_input("Entrada correcta", key="corr_in")
    hora_out = cols[1].time_input("Salida correcta", key="corr_out")
    motivo = st.text_area(
        "Explica qué pasó",
        key="corr_reason",
        placeholder="Olvidé marcar la salida porque salí directo a una reunión…",
        max_chars=400,
    )

    if st.button("Enviar solicitud", type="primary", width="stretch"):
        if len(motivo.strip()) < 10:
            st.warning("Describe el motivo con un poco más de detalle.")
            return
        from ..tz import combine_gt, gt_to_utc_iso
        try:
            db.client().table("correction_requests").insert({
                "employee_id": profile["id"],
                "work_date": str(dia),
                "requested_clock_in": gt_to_utc_iso(combine_gt(dia, hora_in)),
                "requested_clock_out": gt_to_utc_iso(combine_gt(dia, hora_out)),
                "reason": motivo.strip(),
                "status": "pending",
            }).execute()
            st.success("Solicitud enviada. La gerencia la revisará.")
        except Exception as exc:
            st.error(db.error_message(exc))


def render() -> None:
    profile = auth.current_profile()
    user_id = auth.current_user_id()

    start, end = _range_picker("hist")

    attendance = db.fetch_attendance(start, end, employee_id=user_id)
    exceptions = db.fetch_exceptions(start, end, employee_id=user_id)
    holidays = db.fetch_holidays(start, end)
    grid = analytics.build_grid([profile], attendance, exceptions, holidays, start, end)

    if grid.empty:
        st.info("No hay información en el período seleccionado.")
        return

    laborales = grid[grid["laboral"] & (grid["estado"] != "future")]
    trabajadas = grid["neto_min"].sum()
    esperadas = laborales["esperado_min"].sum()
    diferencia = grid["acreditado_min"].sum() - esperadas

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(theme.stat("Horas trabajadas", minutes_to_hhmm(trabajadas)), unsafe_allow_html=True)
    c2.markdown(theme.stat("Horas esperadas", minutes_to_hhmm(esperadas)), unsafe_allow_html=True)
    c3.markdown(
        theme.stat("Diferencia", minutes_to_hhmm(diferencia),
                   color=COLORS["success"] if diferencia >= 0 else COLORS["danger"]),
        unsafe_allow_html=True,
    )
    c4.markdown(
        theme.stat("Tardanzas", str(int((grid["estado"].isin(["late", "late_and_early"])).sum())),
                   sub=f"{int(grid['tarde_min'].sum())} minutos en total"),
        unsafe_allow_html=True,
    )

    st.write("")
    st.markdown(f"**{fmt_date(start)} — {fmt_date(end)}**")
    st.markdown(calendar_html(grid, start, end), unsafe_allow_html=True)

    st.dataframe(
        detail_table(grid.sort_values("fecha", ascending=False)),
        width="stretch",
        hide_index=True,
        height=460,
    )

    with st.expander("Solicitar una corrección"):
        _request_correction(profile, grid)

    pendientes = db.fetch_correction_requests()
    mias = [r for r in pendientes if r["employee_id"] == user_id]
    if mias:
        with st.expander(f"Mis solicitudes ({len(mias)})"):
            for r in mias[:20]:
                estado = {"pending": "En revisión", "approved": "Aprobada",
                          "rejected": "Rechazada"}.get(r["status"], r["status"])
                st.markdown(
                    f"- **{fmt_date_short(date.fromisoformat(r['work_date']))}** · {estado}"
                    + (f" · _{r.get('review_note') or ''}_" if r.get("review_note") else "")
                )
