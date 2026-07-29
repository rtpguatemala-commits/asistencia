"""Generación del reporte de horas trabajadas en Excel."""

from __future__ import annotations

import streamlit as st

from .. import analytics, auth, db, reports, theme
from ..config import COLORS
from ..tz import fmt_date, minutes_to_hhmm
from .history import _range_picker


def render() -> None:
    if not auth.require_admin():
        return

    employees = db.fetch_employees(include_inactive=True)
    if not employees:
        st.info("Todavía no hay empleados registrados.")
        return

    st.markdown("Elige el período y los empleados; la app arma el archivo de Excel.")

    start, end = _range_picker("rep")

    nombres = [e["full_name"] for e in employees]
    elegidos = st.multiselect("Empleados", nombres, default=nombres, key="rep_emp")
    incluir_inactivos = st.checkbox("Incluir empleados inactivos", value=False, key="rep_inact")

    seleccionados = [e for e in employees if e["full_name"] in elegidos]
    if not incluir_inactivos:
        seleccionados = [e for e in seleccionados if e.get("is_active", True)]

    if not seleccionados:
        st.warning("Selecciona al menos un empleado activo.")
        return

    attendance = db.fetch_attendance(start, end)
    exceptions = db.fetch_exceptions(start, end)
    holidays = db.fetch_holidays(start, end)
    grid = analytics.build_grid(seleccionados, attendance, exceptions, holidays, start, end)

    if grid.empty:
        st.info("No hay datos en el período seleccionado.")
        return

    resumen = analytics.summarize(grid)
    laborales = grid[grid["laboral"] & (grid["estado"] != "future")]

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(theme.stat("Empleados", str(len(seleccionados))), unsafe_allow_html=True)
    c2.markdown(theme.stat("Días del reporte", str(len(grid))), unsafe_allow_html=True)
    c3.markdown(theme.stat("Horas trabajadas", minutes_to_hhmm(grid["neto_min"].sum())),
                unsafe_allow_html=True)
    c4.markdown(theme.stat("Horas esperadas", minutes_to_hhmm(laborales["esperado_min"].sum())),
                unsafe_allow_html=True)

    st.write("")
    st.markdown("##### Vista previa del resumen")
    st.dataframe(resumen.drop(columns=["employee_id"]), width="stretch", hide_index=True)

    incidencias = analytics.incidents(grid)
    st.caption(
        f"El archivo incluirá {len(grid)} filas de detalle, "
        f"{len(resumen)} filas de resumen, {len(incidencias)} incidencias y 2 gráficas."
    )

    if st.button("Generar reporte de Excel", type="primary", width="stretch"):
        with st.spinner("Armando el archivo…"):
            contenido = reports.build_report(
                grid, start, end,
                generated_by=auth.current_profile().get("full_name", ""),
            )
        st.session_state["report_bytes"] = contenido
        st.session_state["report_name"] = reports.report_filename(start, end)
        st.success("Reporte listo.")

    if st.session_state.get("report_bytes"):
        st.download_button(
            "Descargar reporte",
            data=st.session_state["report_bytes"],
            file_name=st.session_state.get("report_name", "reporte.xlsx"),
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch",
        )
