"""Inicio de sesión, sesión activa y control de roles."""

from __future__ import annotations

from typing import Any

import streamlit as st

from . import db


def _apply_session(access_token: str, refresh_token: str) -> None:
    st.session_state.access_token = access_token
    st.session_state.refresh_token = refresh_token
    try:
        db.client().postgrest.auth(access_token)
    except Exception:
        pass


def sign_in(email: str, password: str) -> tuple[bool, str]:
    """Devuelve (ok, mensaje)."""
    try:
        st.session_state.sb_client = db.new_client()
        res = db.client().auth.sign_in_with_password(
            {"email": email.strip().lower(), "password": password}
        )
        if not res or not res.session:
            return False, "No se pudo iniciar sesión."
        _apply_session(res.session.access_token, res.session.refresh_token)
        st.session_state.user_id = res.user.id

        profile = load_profile(res.user.id)
        if profile is None:
            sign_out()
            return False, ("Tu cuenta existe pero no tiene perfil de empleado. "
                           "Pídele a la gerencia que te registre en el sistema.")
        if not profile.get("is_active", True):
            sign_out()
            return False, "Tu usuario está inactivo. Contacta a la gerencia."

        st.session_state.profile = profile
        return True, ""
    except Exception as exc:
        return False, db.error_message(exc)


def sign_out() -> None:
    try:
        db.client().auth.sign_out()
    except Exception:
        pass
    for key in ("sb_client", "access_token", "refresh_token", "user_id", "profile",
                "geo", "geo_ts", "clock_feedback"):
        st.session_state.pop(key, None)


def load_profile(user_id: str) -> dict[str, Any] | None:
    rows = (
        db.client().table("employees").select("*").eq("id", user_id).limit(1).execute().data
        or []
    )
    return rows[0] if rows else None


def refresh_profile() -> None:
    uid = st.session_state.get("user_id")
    if uid:
        profile = load_profile(uid)
        if profile:
            st.session_state.profile = profile


def is_authenticated() -> bool:
    return bool(st.session_state.get("user_id") and st.session_state.get("profile"))


def current_profile() -> dict[str, Any]:
    return st.session_state.get("profile", {})


def current_user_id() -> str | None:
    return st.session_state.get("user_id")


def is_admin() -> bool:
    return current_profile().get("role") == "admin"


def require_admin() -> bool:
    if not is_admin():
        st.error("Esta sección es solo para la gerencia.")
        return False
    return True


def change_password(new_password: str) -> tuple[bool, str]:
    try:
        db.client().auth.update_user({"password": new_password})
        return True, "Contraseña actualizada."
    except Exception as exc:
        return False, db.error_message(exc)


def send_password_reset(email: str) -> tuple[bool, str]:
    try:
        db.new_client().auth.reset_password_email(email.strip().lower())
        return True, "Si el correo existe, te enviamos un enlace para restablecer la contraseña."
    except Exception as exc:
        return False, db.error_message(exc)


# ---------------------------------------------------------------------
# Alta de usuarios (requiere clave service_role)
# ---------------------------------------------------------------------
def admin_available() -> bool:
    return db.admin_client() is not None


def create_employee_account(email: str, password: str, full_name: str) -> tuple[bool, str, str | None]:
    """Crea el usuario en Auth. Devuelve (ok, mensaje, user_id)."""
    admin = db.admin_client()
    if admin is None:
        return False, ("Falta la clave service_role en los secretos de la app. "
                       "Sin ella no se pueden crear usuarios desde aquí."), None
    try:
        res = admin.auth.admin.create_user({
            "email": email.strip().lower(),
            "password": password,
            "email_confirm": True,
            "user_metadata": {"full_name": full_name},
        })
        return True, "Usuario creado.", res.user.id
    except Exception as exc:
        return False, db.error_message(exc), None


def admin_set_password(user_id: str, password: str) -> tuple[bool, str]:
    admin = db.admin_client()
    if admin is None:
        return False, "Falta la clave service_role en los secretos de la app."
    try:
        admin.auth.admin.update_user_by_id(user_id, {"password": password})
        return True, "Contraseña restablecida."
    except Exception as exc:
        return False, db.error_message(exc)


def admin_delete_account(user_id: str) -> tuple[bool, str]:
    admin = db.admin_client()
    if admin is None:
        return False, "Falta la clave service_role en los secretos de la app."
    try:
        admin.auth.admin.delete_user(user_id)
        return True, "Cuenta eliminada."
    except Exception as exc:
        return False, db.error_message(exc)
