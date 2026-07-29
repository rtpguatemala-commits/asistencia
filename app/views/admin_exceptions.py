"""Excepciones: vacaciones, incapacidades, permisos y asuetos."""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from .. import auth, db, theme
from ..config import COLORS, EXCEPTION_LABELS
from ..tz import fmt_date_short, today_gt


def _tab_registrar(employees: list[dict]) -> None:
    mapa = {e["full_name"]: e["id"] for e in employees}
    if not mapa:
        st.info("Primero registra empleados.")
        return

    with st.form("form_exception"):
        nombres = st.multiselect("Empleados", list(mapa.keys()), key="exc_emp")
        c1, c2 = st.columns(2)
        desde = c1.date_input("Desde", value=today_gt(), format="DD/MM/YYYY", key="exc_from")
        hasta = c2.date_input("Hasta", value=today_gt(), format="DD/MM/YYYY", key="exc_to")
        tipo = st.selectbox(
            "Tipo", list(EXCEPTION_LABELS.keys()),
            format_func=lambda t: EXCEPTION_LABELS[t], key="exc_type",
        )
        pagado = st.checkbox(
            "Cuenta como horas pagadas", value=True, key="exc_paid",
            help="Si está marcado, esos días suman a las horas acreditadas del reporte.",
        )
        nota = st.text_area("Nota", key="exc_note", max_chars=300,
                            placeholder="Vacaciones aprobadas según solicitud del 10 de julio.")
        adjunto = st.text_input(
            "Enlace a documento de respaldo (opcional)", key="exc_url",
            placeholder="https://drive.google.com/…",
        )
        enviar = st.form_submit_button("Registrar excepción", type="primary",
                                       width="stretch")

    if enviar:
        if not nombres:
            st.warning("Elige al menos un empleado.")
            return
        if hasta < desde:
            st.warning("La fecha final no puede ser anterior a la inicial.")
            return
        filas = [{
            "employee_id": mapa[n],
            "date_from": str(desde),
            "date_to": str(hasta),
            "type": tipo,
            "note": nota.strip() or None,
            "attachment_url": adjunto.strip() or None,
            "counts_as_paid": bool(pagado),
            "created_by": auth.current_user_id(),
        } for n in nombres]
        try:
            db.client().table("exceptions").insert(filas).execute()
            st.success(f"Excepción registrada para {len(filas)} persona(s).")
            st.rerun()
        except Exception as exc:
            st.error(db.error_message(exc))


def _tab_listado(employees: list[dict]) -> None:
    mapa = {e["id"]: e["full_name"] for e in employees}
    registros = db.fetch_exceptions()
    if not registros:
        st.info("No hay excepciones registradas.")
        return

    filas = [{
        "Empleado": mapa.get(r["employee_id"], "—"),
        "Tipo": EXCEPTION_LABELS.get(r["type"], r["type"]),
        "Desde": fmt_date_short(date.fromisoformat(r["date_from"])),
        "Hasta": fmt_date_short(date.fromisoformat(r["date_to"])),
        "Días": (date.fromisoformat(r["date_to"]) - date.fromisoformat(r["date_from"])).days + 1,
        "Pagado": "Sí" if r.get("counts_as_paid") else "No",
        "Nota": r.get("note") or "",
        "_id": r["id"],
    } for r in registros]

    df = pd.DataFrame(filas)
    st.dataframe(df.drop(columns=["_id"]), width="stretch", hide_index=True)

    with st.expander("Eliminar una excepción"):
        opciones = {
            f"{f['Empleado']} · {f['Tipo']} · {f['Desde']} a {f['Hasta']}": f["_id"]
            for f in filas
        }
        elegido = st.selectbox("Excepción", list(opciones.keys()), key="exc_del")
        if st.button("Eliminar", width="stretch"):
            try:
                db.client().table("exceptions").delete().eq("id", opciones[elegido]).execute()
                st.success("Excepción eliminada.")
                st.rerun()
            except Exception as exc:
                st.error(db.error_message(exc))


def _tab_asuetos() -> None:
    hoy = today_gt()
    registros = db.fetch_holidays(date(hoy.year, 1, 1), date(hoy.year + 2, 12, 31))
    if registros:
        df = pd.DataFrame([{
            "Fecha": fmt_date_short(date.fromisoformat(h["date"])),
            "Asueto": h["name"],
            "Medio día": "Sí" if h.get("is_half_day") else "No",
            "_id": h["id"],
        } for h in registros])
        st.dataframe(df.drop(columns=["_id"]), width="stretch", hide_index=True, height=400)
    else:
        st.info("No hay asuetos cargados. Ejecuta el script 04_seed_holidays.sql.")
        df = pd.DataFrame()

    c1, c2 = st.columns(2)
    with c1.form("form_holiday"):
        st.markdown("**Agregar asueto**")
        fecha = st.date_input("Fecha", value=hoy, format="DD/MM/YYYY", key="hol_date")
        nombre = st.text_input("Nombre", key="hol_name")
        medio = st.checkbox("Solo medio día", key="hol_half")
        if st.form_submit_button("Agregar", width="stretch"):
            if not nombre.strip():
                st.warning("Escribe el nombre del asueto.")
            else:
                try:
                    db.client().table("holidays").insert({
                        "date": str(fecha), "name": nombre.strip(), "is_half_day": bool(medio),
                    }).execute()
                    st.success("Asueto agregado.")
                    st.rerun()
                except Exception as exc:
                    st.error(db.error_message(exc))

    if not df.empty:
        with c2.form("form_holiday_del"):
            st.markdown("**Quitar asueto**")
            opciones = {f"{r['Fecha']} · {r['Asueto']}": r["_id"] for _, r in df.iterrows()}
            elegido = st.selectbox("Asueto", list(opciones.keys()), key="hol_del")
            if st.form_submit_button("Quitar", width="stretch"):
                try:
                    db.client().table("holidays").delete().eq("id", opciones[elegido]).execute()
                    st.success("Asueto eliminado.")
                    st.rerun()
                except Exception as exc:
                    st.error(db.error_message(exc))


def render() -> None:
    if not auth.require_admin():
        return
    employees = db.fetch_employees(include_inactive=True)
    tab1, tab2, tab3 = st.tabs(["Registrar", "Excepciones registradas", "Asuetos"])
    with tab1:
        _tab_registrar(employees)
    with tab2:
        _tab_listado(employees)
    with tab3:
        _tab_asuetos()
