"""Panel en vivo de la gerencia."""

from __future__ import annotations

import streamlit as st

from .. import analytics, auth, db, theme
from ..config import COLORS, MONTH_NAMES
from ..tz import fmt_date, fmt_time, hhmm, minutes_to_hhmm, now_gt, today_gt


def render() -> None:
    if not auth.require_admin():
        return

    hoy = today_gt()
    employees = db.fetch_employees()
    attendance = db.fetch_attendance(hoy, hoy)
    exceptions = db.fetch_exceptions(hoy, hoy)
    holidays = db.fetch_holidays(hoy, hoy)
    grid = analytics.build_grid(employees, attendance, exceptions, holidays, hoy, hoy)

    st.markdown(f"#### {fmt_date(hoy)} · {now_gt().strftime('%H:%M')} hora de Guatemala")

    if grid.empty:
        st.info("Todavía no hay empleados registrados.")
        return

    dentro = grid[grid["estado"] == "open"]
    completados = grid[grid["neto_min"] > 0]
    sin_marcar = grid[(grid["estado"] == "absent") | (grid["estado"] == "future")]
    sin_marcar = sin_marcar[sin_marcar["laboral"]]
    tarde = grid[grid["estado"].isin(["late", "late_and_early"])]

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(theme.stat("En jornada ahora", str(len(dentro)), color=COLORS["info"]),
                unsafe_allow_html=True)
    c2.markdown(theme.stat("Jornada completada", str(len(completados)), color=COLORS["success"]),
                unsafe_allow_html=True)
    c3.markdown(theme.stat("Sin marcar hoy", str(len(sin_marcar)),
                           color=COLORS["danger"] if len(sin_marcar) else COLORS["text"]),
                unsafe_allow_html=True)
    c4.markdown(theme.stat("Llegaron tarde", str(len(tarde)),
                           color=COLORS["warning"] if len(tarde) else COLORS["text"]),
                unsafe_allow_html=True)

    st.write("")

    # ------------- Tarjetas por empleado -------------
    st.markdown("#### Estado de cada persona")
    for _, row in grid.sort_values("empleado").iterrows():
        entrada = hhmm(row["entrada"])
        salida = hhmm(row["salida"])
        lugar = {"building": "Edificio", "other": "Otro lugar"}.get(row["modo_entrada"], "—")
        extra = ""
        if row["excepcion"]:
            extra = f' · <span style="color:{COLORS["info"]}">{row["excepcion"]}</span>'
        elif row["asueto"]:
            extra = f' · <span style="color:{COLORS["muted"]}">{row["asueto"]}</span>'
        elif row["motivo_ubicacion"]:
            extra = f' · <span style="color:{COLORS["muted"]}">{row["motivo_ubicacion"]}</span>'

        st.markdown(
            f"""
<div class="rdp-card" style="display:flex;align-items:center;gap:1rem;flex-wrap:wrap">
  <div style="flex:1 1 190px">
    <div style="font-weight:700">{row['empleado']}</div>
    <div style="font-size:.76rem;color:{COLORS['muted']}">{row['cargo'] or '—'} · {row['horario']}</div>
  </div>
  <div style="font-size:.86rem;color:{COLORS['muted']}">
    Entrada <b style="color:{COLORS['text']}">{entrada}</b> ·
    Salida <b style="color:{COLORS['text']}">{salida}</b> ·
    {lugar}{extra}
  </div>
  <div style="margin-left:auto">{theme.badge(row['estado'])}</div>
</div>
""",
            unsafe_allow_html=True,
        )

    # ------------- Alertas -------------
    st.write("")
    st.markdown("#### Alertas")
    alertas = []

    if len(sin_marcar):
        nombres = ", ".join(sin_marcar["empleado"].tolist())
        alertas.append(("warn", f"Sin marcar entrada hoy: <b>{nombres}</b>."))

    abiertas = (
        db.client().table("attendance").select("employee_id, work_date")
        .is_("clock_out_at", "null").not_.is_("clock_in_at", "null")
        .lt("work_date", str(hoy)).execute().data or []
    )
    if abiertas:
        mapa = {e["id"]: e["full_name"] for e in employees}
        detalle = ", ".join(f"{mapa.get(a['employee_id'], '—')} ({a['work_date']})" for a in abiertas)
        alertas.append(("error", f"Jornadas abiertas de días anteriores: <b>{detalle}</b>."))

    revisar = (
        db.client().table("attendance").select("employee_id, work_date")
        .eq("needs_review", True).order("work_date", desc=True).limit(20).execute().data or []
    )
    if revisar:
        alertas.append(("warn", f"Hay <b>{len(revisar)}</b> registros marcados para revisión."))

    pendientes = db.fetch_correction_requests(status="pending")
    if pendientes:
        alertas.append(("info", f"Hay <b>{len(pendientes)}</b> solicitudes de corrección esperando respuesta."))

    cumples = analytics.upcoming_birthdays(employees, horizon_days=15)
    for c in cumples:
        cuando = "hoy" if c["faltan"] == 0 else ("mañana" if c["faltan"] == 1 else f"en {c['faltan']} días")
        alertas.append(("info", f"🎂 Cumpleaños de <b>{c['nombre']}</b> {cuando} "
                                f"({c['proximo'].day} de {MONTH_NAMES[c['proximo'].month].lower()})."))

    if not alertas:
        st.markdown(theme.note("Todo en orden. No hay alertas pendientes.", "ok"),
                    unsafe_allow_html=True)
    else:
        for kind, texto in alertas:
            st.markdown(theme.note(texto, kind), unsafe_allow_html=True)

    st.write("")
    if st.button("Actualizar panel", width="stretch"):
        st.rerun()
