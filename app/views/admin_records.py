"""Todos los registros de asistencia, con filtros y edición manual."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from .. import analytics, auth, db, theme
from ..config import COLORS, STATUS_LABELS
from ..tz import (
    combine_gt,
    fmt_date_short,
    gt_to_utc_iso,
    minutes_to_hhmm,
    now_gt,
    parse_date,
    to_gt,
)
from .history import _range_picker, detail_table


def _editor(employees: list[dict]) -> None:
    st.markdown("Corrige manualmente un registro. Todo cambio queda en la bitácora.")
    mapa = {e["full_name"]: e["id"] for e in employees}
    nombre = st.selectbox("Empleado", list(mapa.keys()), key="edit_emp")
    dia = st.date_input("Fecha", key="edit_date", format="DD/MM/YYYY")

    emp_id = mapa[nombre]
    existente = (
        db.client().table("attendance").select("*")
        .eq("employee_id", emp_id).eq("work_date", str(dia)).limit(1).execute().data or []
    )
    registro = existente[0] if existente else None

    if registro:
        ent = to_gt(registro.get("clock_in_at"))
        sal = to_gt(registro.get("clock_out_at"))
        st.caption(
            f"Registro actual: entrada {ent.strftime('%H:%M') if ent else '—'}, "
            f"salida {sal.strftime('%H:%M') if sal else '—'}, "
            f"estado {STATUS_LABELS.get(registro.get('status'), '—')}."
        )
    else:
        st.caption("No hay registro para esa fecha. Se creará uno nuevo.")
        ent = sal = None

    cols = st.columns(2)
    hora_in = cols[0].time_input("Entrada", value=ent.time() if ent else None, key="edit_in")
    hora_out = cols[1].time_input("Salida", value=sal.time() if sal else None, key="edit_out")
    nota = st.text_input("Observación", value=(registro or {}).get("note") or "", key="edit_note")

    b1, b2 = st.columns(2)
    if b1.button("Guardar registro", type="primary", width="stretch"):
        payload = {
            "employee_id": emp_id,
            "work_date": str(dia),
            "clock_in_at": gt_to_utc_iso(combine_gt(dia, hora_in)) if hora_in else None,
            "clock_out_at": gt_to_utc_iso(combine_gt(dia, hora_out)) if hora_out else None,
            "note": nota or None,
            "needs_review": False,
            "auto_closed": False,
            "edited_by": auth.current_user_id(),
            "edited_at": gt_to_utc_iso(now_gt()),
        }
        try:
            db.client().table("attendance").upsert(
                payload, on_conflict="employee_id,work_date"
            ).execute()
            db.log_action(auth.current_user_id(), auth.current_profile().get("full_name"),
                          "edit_attendance", "attendance", None,
                          {"employee": nombre, "date": str(dia)})
            st.success("Registro guardado.")
            st.rerun()
        except Exception as exc:
            st.error(db.error_message(exc))

    if registro and b2.button("Eliminar registro", width="stretch"):
        try:
            db.client().table("attendance").delete().eq("id", registro["id"]).execute()
            db.log_action(auth.current_user_id(), auth.current_profile().get("full_name"),
                          "delete_attendance", "attendance", registro["id"],
                          {"employee": nombre, "date": str(dia)})
            st.success("Registro eliminado.")
            st.rerun()
        except Exception as exc:
            st.error(db.error_message(exc))


def render() -> None:
    if not auth.require_admin():
        return

    employees = db.fetch_employees(include_inactive=True)
    if not employees:
        st.info("Todavía no hay empleados registrados.")
        return

    start, end = _range_picker("adm")

    nombres = ["Todos"] + [e["full_name"] for e in employees]
    filtro_emp = st.multiselect("Empleados", nombres, default=["Todos"], key="adm_emp")
    filtro_estado = st.multiselect(
        "Estado",
        [STATUS_LABELS[k] for k in
         ("on_time", "late", "early_leave", "late_and_early", "open", "absent",
          "exception", "holiday", "rest")],
        key="adm_status",
    )

    seleccionados = (
        employees if ("Todos" in filtro_emp or not filtro_emp)
        else [e for e in employees if e["full_name"] in filtro_emp]
    )

    attendance = db.fetch_attendance(start, end)
    exceptions = db.fetch_exceptions(start, end)
    holidays = db.fetch_holidays(start, end)
    grid = analytics.build_grid(seleccionados, attendance, exceptions, holidays, start, end)

    if grid.empty:
        st.info("No hay datos en el período seleccionado.")
        return

    if filtro_estado:
        grid = grid[grid["estado_texto"].isin(filtro_estado)]

    resumen = analytics.summarize(grid)

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(theme.stat("Registros", str(len(grid))), unsafe_allow_html=True)
    c2.markdown(theme.stat("Horas trabajadas", minutes_to_hhmm(grid["neto_min"].sum())),
                unsafe_allow_html=True)
    c3.markdown(theme.stat("Tardanzas",
                           str(int(grid["estado"].isin(["late", "late_and_early"]).sum())),
                           color=COLORS["warning"]), unsafe_allow_html=True)
    c4.markdown(theme.stat("Ausencias", str(int((grid["estado"] == "absent").sum())),
                           color=COLORS["danger"]), unsafe_allow_html=True)

    st.write("")
    tab1, tab2, tab3 = st.tabs(["Detalle", "Resumen por empleado", "Corregir un registro"])

    with tab1:
        vista = detail_table(grid.sort_values(["fecha", "empleado"], ascending=[False, True]))
        vista.insert(0, "Empleado", grid.sort_values(
            ["fecha", "empleado"], ascending=[False, True])["empleado"].values)
        st.dataframe(vista, width="stretch", hide_index=True, height=520)

    with tab2:
        if resumen.empty:
            st.info("Sin datos.")
        else:
            st.dataframe(
                resumen.drop(columns=["employee_id"]),
                width="stretch", hide_index=True,
            )

    with tab3:
        _editor(employees)
