"""Alta y edición de empleados."""

from __future__ import annotations

import secrets
import string
from datetime import date, time

import pandas as pd
import streamlit as st

from .. import analytics, auth, db, theme
from ..config import COLORS, DAY_NAMES
from ..tz import fmt_date_short, minutes_to_hhmm, parse_date, parse_time

DAY_OPTIONS = {DAY_NAMES[i]: i for i in range(1, 8)}


def _random_password(length: int = 10) -> str:
    alphabet = string.ascii_letters + string.digits
    return "Rdp" + "".join(secrets.choice(alphabet) for _ in range(length))


def _employee_form(prefix: str, data: dict | None = None) -> dict:
    data = data or {}
    c1, c2 = st.columns(2)
    nombre = c1.text_input("Nombre completo", value=data.get("full_name", ""), key=f"{prefix}_name")
    correo = c2.text_input("Correo electrónico", value=data.get("email", ""), key=f"{prefix}_email",
                           disabled=bool(data))
    c3, c4 = st.columns(2)
    cargo = c3.text_input("Cargo", value=data.get("position") or "", key=f"{prefix}_pos")
    rol = c4.selectbox(
        "Rol", ["employee", "admin"],
        index=0 if data.get("role", "employee") == "employee" else 1,
        format_func=lambda r: "Colaborador" if r == "employee" else "Gerencia",
        key=f"{prefix}_role",
    )

    c5, c6 = st.columns(2)
    nacimiento = c5.date_input(
        "Fecha de nacimiento",
        value=parse_date(data.get("birth_date")),
        min_value=date(1940, 1, 1),
        max_value=date.today(),
        format="DD/MM/YYYY",
        key=f"{prefix}_bd",
    )
    telefono = c6.text_input("Teléfono", value=data.get("phone") or "", key=f"{prefix}_phone")

    c7, c8 = st.columns(2)
    entrada = c7.time_input(
        "Hora de entrada",
        value=parse_time(data.get("shift_start")) or time(8, 0),
        key=f"{prefix}_in",
    )
    salida = c8.time_input(
        "Hora de salida",
        value=parse_time(data.get("shift_end")) or time(17, 0),
        key=f"{prefix}_out",
    )

    dias_actuales = data.get("work_days") or [1, 2, 3, 4, 5]
    dias = st.multiselect(
        "Días laborales",
        list(DAY_OPTIONS.keys()),
        default=[DAY_NAMES[d] for d in dias_actuales],
        key=f"{prefix}_days",
    )

    c9, c10, c11 = st.columns(3)
    umbral = c9.number_input(
        "Descontar almuerzo si la jornada supera (horas)",
        min_value=0.0, max_value=12.0, step=0.5,
        value=float(data.get("lunch_threshold_hours") or 6.0),
        key=f"{prefix}_thr",
    )
    descuento = c10.number_input(
        "Minutos de almuerzo a descontar",
        min_value=0, max_value=180, step=15,
        value=int(data.get("lunch_deduction_minutes") or 60),
        key=f"{prefix}_lunch",
    )
    tolerancia = c11.number_input(
        "Tolerancia (minutos)",
        min_value=0, max_value=60, step=5,
        value=int(data.get("grace_minutes") or 15),
        key=f"{prefix}_grace",
    )

    activo = st.checkbox("Usuario activo", value=bool(data.get("is_active", True)),
                         key=f"{prefix}_active")

    return {
        "full_name": nombre.strip(),
        "email": correo.strip().lower(),
        "position": cargo.strip() or None,
        "role": rol,
        "birth_date": str(nacimiento) if nacimiento else None,
        "phone": telefono.strip() or None,
        "shift_start": entrada.strftime("%H:%M"),
        "shift_end": salida.strftime("%H:%M"),
        "work_days": sorted(DAY_OPTIONS[d] for d in dias) or [1, 2, 3, 4, 5],
        "lunch_threshold_hours": float(umbral),
        "lunch_deduction_minutes": int(descuento),
        "grace_minutes": int(tolerancia),
        "is_active": bool(activo),
    }


def _tab_listado(employees: list[dict]) -> None:
    if not employees:
        st.info("Todavía no hay empleados.")
        return
    filas = []
    for e in employees:
        filas.append({
            "Empleado": e["full_name"],
            "Correo": e["email"],
            "Cargo": e.get("position") or "—",
            "Rol": "Gerencia" if e.get("role") == "admin" else "Colaborador",
            "Horario": analytics.schedule_label(e),
            "Días": ", ".join(DAY_NAMES[d][:3] for d in (e.get("work_days") or [])),
            "Jornada": minutes_to_hhmm(analytics.expected_minutes(e)),
            "Nacimiento": fmt_date_short(parse_date(e.get("birth_date"))),
            "Estado": "Activo" if e.get("is_active") else "Inactivo",
        })
    st.dataframe(pd.DataFrame(filas), width="stretch", hide_index=True)


def _tab_nuevo() -> None:
    if not auth.admin_available():
        st.warning(
            "Para crear usuarios desde aquí hace falta la clave **service_role** "
            "en los secretos de la app (SUPABASE_SERVICE_KEY). Mientras tanto puedes "
            "crear el usuario desde Supabase → Authentication → Add user, y luego "
            "completar su perfil en la pestaña *Editar*."
        )
        return

    datos = _employee_form("new")
    generar = st.checkbox("Generar contraseña temporal automáticamente", value=True, key="new_gen")
    if generar:
        password = st.session_state.setdefault("new_generated_pwd", _random_password())
        st.code(password, language=None)
        st.caption("Cópiala y entrégasela a la persona. Podrá cambiarla desde Mi perfil.")
    else:
        password = st.text_input("Contraseña inicial", type="password", key="new_pwd")

    if st.button("Crear empleado", type="primary", width="stretch"):
        if not datos["full_name"] or not datos["email"]:
            st.warning("El nombre y el correo son obligatorios.")
            return
        if len(password) < 8:
            st.warning("La contraseña debe tener al menos 8 caracteres.")
            return

        ok, mensaje, user_id = auth.create_employee_account(
            datos["email"], password, datos["full_name"]
        )
        if not ok:
            st.error(mensaje)
            return
        try:
            db.client().table("employees").insert({"id": user_id, **datos}).execute()
            db.log_action(auth.current_user_id(), auth.current_profile().get("full_name"),
                          "create_employee", "employees", user_id, {"email": datos["email"]})
            st.session_state.pop("new_generated_pwd", None)
            st.success(f"{datos['full_name']} fue creado. Contraseña temporal: {password}")
        except Exception as exc:
            st.error(
                "El usuario se creó en Auth pero falló al guardar el perfil: "
                + db.error_message(exc)
            )


def _tab_editar(employees: list[dict]) -> None:
    if not employees:
        st.info("Todavía no hay empleados.")
        return
    mapa = {f"{e['full_name']} · {e['email']}": e for e in employees}
    etiqueta = st.selectbox("Empleado", list(mapa.keys()), key="edit_pick")
    empleado = mapa[etiqueta]

    datos = _employee_form(f"edit_{empleado['id'][:8]}", empleado)

    c1, c2 = st.columns(2)
    if c1.button("Guardar cambios", type="primary", width="stretch"):
        payload = {k: v for k, v in datos.items() if k != "email"}
        try:
            db.client().table("employees").update(payload).eq("id", empleado["id"]).execute()
            db.log_action(auth.current_user_id(), auth.current_profile().get("full_name"),
                          "update_employee", "employees", empleado["id"], payload)
            st.success("Cambios guardados.")
            if empleado["id"] == auth.current_user_id():
                auth.refresh_profile()
            st.rerun()
        except Exception as exc:
            st.error(db.error_message(exc))

    with c2.popover("Restablecer contraseña", width="stretch"):
        nueva = _random_password()
        st.code(nueva, language=None)
        if st.button("Aplicar esta contraseña", key="reset_apply"):
            ok, mensaje = auth.admin_set_password(empleado["id"], nueva)
            (st.success if ok else st.error)(mensaje)

    st.divider()
    with st.expander("Dar de baja definitivamente"):
        st.caption(
            "Recomendación: en lugar de borrar, desmarca *Usuario activo*. "
            "Así conservas todo su historial. Borrar elimina también sus registros."
        )
        confirmar = st.text_input(
            f'Escribe "{empleado["full_name"]}" para confirmar', key="del_confirm"
        )
        if st.button("Eliminar cuenta y su historial", width="stretch"):
            if confirmar.strip() != empleado["full_name"]:
                st.warning("El nombre no coincide.")
            elif empleado["id"] == auth.current_user_id():
                st.error("No puedes eliminar tu propia cuenta.")
            else:
                ok, mensaje = auth.admin_delete_account(empleado["id"])
                if ok:
                    st.success("Cuenta eliminada.")
                    st.rerun()
                else:
                    st.error(mensaje)


def render() -> None:
    if not auth.require_admin():
        return
    employees = db.fetch_employees(include_inactive=True)
    tab1, tab2, tab3 = st.tabs(["Listado", "Nuevo empleado", "Editar"])
    with tab1:
        _tab_listado(employees)
    with tab2:
        _tab_nuevo()
    with tab3:
        _tab_editar(employees)
