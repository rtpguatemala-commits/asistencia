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

    # url_path debe ser único en cada página: todas las vistas exponen una función
    # llamada render(), y Streamlit deriva la ruta del nombre de la función si no
    # se le indica una. Sin esto, la navegación falla con "pathnames must be unique".
    paginas_empleado = [
        st.Page(clock.render, title="Marcar jornada", icon=":material/schedule:",
                url_path="marcar", default=True),
        st.Page(history.render, title="Mi historial", icon=":material/calendar_month:",
                url_path="historial"),
        st.Page(stats.render, title="Mis estadísticas", icon=":material/insights:",
                url_path="estadisticas"),
        st.Page(birthdays.render, title="Cumpleaños", icon=":material/cake:",
                url_path="cumpleanos"),
        st.Page(profile.render, title="Mi perfil", icon=":material/person:",
                url_path="perfil"),
    ]

    if es_admin:
        paginas_admin = [
            st.Page(admin_live.render, title="Panel en vivo", icon=":material/monitor_heart:",
                    url_path="panel"),
            st.Page(admin_records.render, title="Todos los registros", icon=":material/table_rows:",
                    url_path="registros"),
            st.Page(admin_employees.render, title="Empleados", icon=":material/groups:",
                    url_path="empleados"),
            st.Page(admin_exceptions.render, title="Excepciones y asuetos", icon=":material/event_busy:",
                    url_path="excepciones"),
            st.Page(admin_requests.render, title="Solicitudes", icon=":material/inbox:",
                    url_path="solicitudes"),
            st.Page(admin_reports.render, title="Reportes", icon=":material/download:",
                    url_path="reportes"),
            st.Page(admin_settings.render, title="Configuración", icon=":material/settings:",
                    url_path="configuracion"),
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
