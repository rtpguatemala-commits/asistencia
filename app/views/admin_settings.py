"""Configuración global del sistema."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from .. import auth, db, geo, theme
from ..config import COLORS
from ..tz import fmt_datetime, to_gt


def render() -> None:
    if not auth.require_admin():
        return

    settings = db.fetch_settings()
    if not settings:
        st.error("No se encontró la fila de configuración. Ejecuta 01_schema.sql.")
        return

    tab1, tab2, tab3 = st.tabs(["Geocerca y tolerancia", "Mapa de referencia", "Bitácora"])

    with tab1:
        with st.form("form_settings"):
            c1, c2 = st.columns(2)
            lat = c1.number_input(
                "Latitud del edificio", value=float(settings.get("building_lat") or 14.606243),
                format="%.7f", step=0.000001,
            )
            lng = c2.number_input(
                "Longitud del edificio", value=float(settings.get("building_lng") or -90.466834),
                format="%.7f", step=0.000001,
            )
            c3, c4 = st.columns(2)
            radio = c3.number_input(
                "Radio permitido (metros)", min_value=10, max_value=1000, step=5,
                value=int(settings.get("building_radius_m") or 50),
                help="Distancia máxima al punto central para poder marcar como 'En el Edificio'.",
            )
            precision = c4.number_input(
                "Precisión mínima aceptable del GPS (metros)",
                min_value=20, max_value=500, step=10,
                value=int(settings.get("max_gps_accuracy_m") or 120),
                help="Si el teléfono reporta un margen de error mayor a este valor, "
                     "se rechaza la marca para evitar falsos positivos.",
            )
            c5, c6 = st.columns(2)
            tolerancia = c5.number_input(
                "Tolerancia por defecto (minutos)", min_value=0, max_value=60, step=5,
                value=int(settings.get("default_grace_minutes") or 15),
                help="Se aplica a los empleados nuevos. Cada persona puede tener la suya.",
            )
            autocierre = c6.checkbox(
                "Cerrar automáticamente las jornadas olvidadas",
                value=bool(settings.get("auto_close_enabled", True)),
            )

            st.divider()
            st.markdown("**Bitácora de tareas**")
            c7, c8 = st.columns(2)
            pedir_bitacora = c7.checkbox(
                "Exigir el reporte de tareas al cerrar la jornada",
                value=bool(settings.get("require_work_summary", True)),
                help="Si lo desactivas, el campo sigue apareciendo pero se puede dejar vacío.",
            )
            minimo_bitacora = c8.number_input(
                "Mínimo de caracteres",
                min_value=0, max_value=500, step=10,
                value=int(settings.get("work_summary_min_chars") or 20),
            )

            guardar = st.form_submit_button("Guardar configuración", type="primary",
                                            width="stretch")

        if guardar:
            try:
                db.client().table("settings").update({
                    "building_lat": lat,
                    "building_lng": lng,
                    "building_radius_m": int(radio),
                    "max_gps_accuracy_m": int(precision),
                    "default_grace_minutes": int(tolerancia),
                    "auto_close_enabled": bool(autocierre),
                    "require_work_summary": bool(pedir_bitacora),
                    "work_summary_min_chars": int(minimo_bitacora),
                }).eq("id", 1).execute()
                db.log_action(auth.current_user_id(), auth.current_profile().get("full_name"),
                              "update_settings", "settings", "1",
                              {"radius": int(radio), "accuracy": int(precision)})
                st.success("Configuración guardada.")
                st.rerun()
            except Exception as exc:
                st.error(db.error_message(exc))

        st.markdown(
            theme.note(
                "Si en la práctica hay rechazos falsos (gente que sí está en la oficina "
                "pero el GPS la ubica lejos), sube el radio a 75 u 80 metros. "
                "Los teléfonos dentro de edificios de concreto suelen tener un margen "
                "de error de 20 a 50 metros.",
                "info",
            ),
            unsafe_allow_html=True,
        )

    with tab2:
        lat0 = float(settings.get("building_lat") or 14.606243)
        lng0 = float(settings.get("building_lng") or -90.466834)
        st.map(pd.DataFrame({"lat": [lat0], "lon": [lng0]}), zoom=16)
        st.caption(
            f"Punto central: {lat0:.6f}, {lng0:.6f} · "
            f"radio de {settings.get('building_radius_m')} metros."
        )
        ubicacion = st.session_state.get("geo")
        if ubicacion:
            distancia = geo.haversine_m(ubicacion["lat"], ubicacion["lng"], lat0, lng0)
            st.caption(
                f"Tu dispositivo está a {distancia:.0f} m del punto central "
                f"(precisión ± {ubicacion['accuracy']:.0f} m)."
            )

    with tab3:
        registros = (
            db.client().table("audit_log").select("*")
            .order("created_at", desc=True).limit(200).execute().data or []
        )
        if not registros:
            st.info("La bitácora está vacía.")
        else:
            df = pd.DataFrame([{
                "Fecha": fmt_datetime(to_gt(r["created_at"])),
                "Quién": r.get("actor_name") or "Sistema",
                "Acción": r["action"],
                "Entidad": r["entity"],
                "Detalle": str(r.get("details") or ""),
            } for r in registros])
            st.dataframe(df, width="stretch", hide_index=True, height=520)
