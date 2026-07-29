"""
Control de Asistencia — Rescue de Planet de Guatemala
Punto de entrada de la aplicación.
"""

from __future__ import annotations

import streamlit as st

from app import auth, db, theme
from app.config import ORG_NAME
from app.views import (
    admin_employees,
    admin_exceptions,
    admin_live,
    admin_records,
    admin_reports,
    admin_requests,
    admin_settings,
    birthdays,
    clock,
    history,
    login,
    profile,
    stats,
)

theme.page_config()
theme.pwa_head()


def _sidebar_footer() -> None:
    perfil = auth.current_profile()
    with st.sidebar:
        st.markdown("---")
        st.markdown(f"**{perfil.get('full_name', '')}**")
        st.caption(perfil.get("email", ""))
        if st.button("Cerrar sesión", width="stretch"):
            auth.sign_out()
            st.rerun()
        st.caption(f"© {ORG_NAME}")


def main() -> None:
    if not auth.is_authenticated():
        login.render()
        return

    theme.inject_css()
    perfil = auth.current_profile()
    es_admin = auth.is_admin()
    theme.header(
        perfil.get("full_name", ""),
        "Gerencia de Recursos Humanos" if es_admin else (perfil.get("position") or "Colaborador"),
    )

    paginas_empleado = [
        st.Page(clock.render, title="Marcar jornada", icon=":material/schedule:", default=True),
        st.Page(history.render, title="Mi historial", icon=":material/calendar_month:"),
        st.Page(stats.render, title="Mis estadísticas", icon=":material/insights:"),
        st.Page(birthdays.render, title="Cumpleaños", icon=":material/cake:"),
        st.Page(profile.render, title="Mi perfil", icon=":material/person:"),
    ]

    if es_admin:
        paginas_admin = [
            st.Page(admin_live.render, title="Panel en vivo", icon=":material/monitor_heart:"),
            st.Page(admin_records.render, title="Todos los registros", icon=":material/table_rows:"),
            st.Page(admin_employees.render, title="Empleados", icon=":material/groups:"),
            st.Page(admin_exceptions.render, title="Excepciones y asuetos", icon=":material/event_busy:"),
            st.Page(admin_requests.render, title="Solicitudes", icon=":material/inbox:"),
            st.Page(admin_reports.render, title="Reportes", icon=":material/download:"),
            st.Page(admin_settings.render, title="Configuración", icon=":material/settings:"),
        ]
        navegacion = st.navigation(
            {"Mi asistencia": paginas_empleado, "Gerencia": paginas_admin}
        )
    else:
        navegacion = st.navigation({"Mi asistencia": paginas_empleado})

    _sidebar_footer()
    navegacion.run()


if __name__ == "__main__":
    main()
