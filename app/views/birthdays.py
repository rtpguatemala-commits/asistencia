"""Cumpleaños del equipo."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from .. import analytics, db, theme
from ..config import COLORS, MONTH_NAMES
from ..tz import fmt_date, today_gt


def render() -> None:
    employees = db.fetch_employees()
    proximos = analytics.upcoming_birthdays(employees, horizon_days=365)

    sin_fecha = [e["full_name"] for e in employees if not e.get("birth_date")]

    if not proximos:
        st.info("Todavía no hay fechas de nacimiento registradas.")
    else:
        st.markdown("#### Próximos cumpleaños")
        cols = st.columns(min(4, len(proximos[:4])) or 1)
        for col, p in zip(cols, proximos[:4]):
            if p["faltan"] == 0:
                sub, color = "¡Hoy!", COLORS["primary"]
            elif p["faltan"] == 1:
                sub, color = "Mañana", COLORS["primary"]
            else:
                sub, color = f"En {p['faltan']} días", COLORS["text"]
            col.markdown(
                theme.stat(
                    p["nombre"],
                    f"{p['proximo'].day} de {MONTH_NAMES[p['proximo'].month].lower()}",
                    sub=f"{sub} · cumple {p['edad']}",
                    color=color,
                ),
                unsafe_allow_html=True,
            )

        st.write("")
        st.markdown("#### Calendario del año")
        tabla = analytics.all_birthdays_by_month(employees)
        if not tabla.empty:
            tabla["Mes"] = tabla["Mes"].map(MONTH_NAMES)
            tabla["Fecha"] = tabla["Fecha"].apply(lambda d: f"{d.day:02d}/{d.month:02d}/{d.year}")
            st.dataframe(
                tabla[["Empleado", "Cargo", "Mes", "Día", "Fecha"]],
                width="stretch",
                hide_index=True,
            )

    if sin_fecha:
        st.caption(
            "Sin fecha de nacimiento registrada: " + ", ".join(sin_fecha)
            + ". La gerencia puede agregarla en la sección Empleados."
        )
