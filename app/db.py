"""Acceso a Supabase: cliente por sesión, cliente administrativo y helpers."""

from __future__ import annotations

from typing import Any

import streamlit as st
from supabase import Client, create_client


def _secret(name: str, default: str = "") -> str:
    try:
        return str(st.secrets[name]).strip()
    except Exception:
        return default


def supabase_url() -> str:
    return _secret("SUPABASE_URL")


def anon_key() -> str:
    return _secret("SUPABASE_ANON_KEY")


def service_key() -> str:
    return _secret("SUPABASE_SERVICE_KEY")


def secrets_ok() -> bool:
    return bool(supabase_url() and anon_key())


def new_client() -> Client:
    """Cliente nuevo, sin sesión. Uno por usuario conectado."""
    return create_client(supabase_url(), anon_key())


@st.cache_resource(show_spinner=False)
def admin_client() -> Client | None:
    """Cliente con clave service_role. Solo para altas de usuario y reseteos.

    Vive únicamente en el servidor de Streamlit; nunca llega al navegador.
    """
    key = service_key()
    if not key:
        return None
    return create_client(supabase_url(), key)


def client() -> Client:
    """Cliente de la sesión actual, ya autenticado si hay sesión iniciada."""
    if "sb_client" not in st.session_state:
        st.session_state.sb_client = new_client()
    return st.session_state.sb_client


# ---------------------------------------------------------------------
# Manejo de errores
# ---------------------------------------------------------------------
def error_message(exc: Exception) -> str:
    """Extrae el mensaje legible de un error de Supabase / PostgREST."""
    for attr in ("message", "msg", "details", "hint"):
        value = getattr(exc, attr, None)
        if value:
            text = str(value)
            break
    else:
        text = str(exc)

    # Los RAISE EXCEPTION de Postgres llegan con prefijos técnicos
    for marker in ("ERROR:", "PostgrestError:"):
        if marker in text:
            text = text.split(marker, 1)[1]
    text = text.strip().strip('"').strip()

    traducciones = {
        "Invalid login credentials": "Correo o contraseña incorrectos.",
        "Email not confirmed": "El correo aún no ha sido confirmado.",
        "User already registered": "Ese correo ya tiene una cuenta.",
        "Password should be at least": "La contraseña es demasiado corta.",
        "JWT expired": "Tu sesión expiró. Vuelve a iniciar sesión.",
    }
    for clave, valor in traducciones.items():
        if clave.lower() in text.lower():
            return valor
    return text or "Ocurrió un error inesperado."


# ---------------------------------------------------------------------
# Consultas comunes
# ---------------------------------------------------------------------
def fetch_employees(include_inactive: bool = False) -> list[dict[str, Any]]:
    query = client().table("employees").select("*").order("full_name")
    if not include_inactive:
        query = query.eq("is_active", True)
    return query.execute().data or []


def fetch_settings() -> dict[str, Any]:
    rows = client().table("settings").select("*").eq("id", 1).limit(1).execute().data or []
    return rows[0] if rows else {}


def fetch_attendance(date_from, date_to, employee_id: str | None = None) -> list[dict[str, Any]]:
    query = (
        client().table("attendance").select("*")
        .gte("work_date", str(date_from))
        .lte("work_date", str(date_to))
        .order("work_date", desc=True)
    )
    if employee_id:
        query = query.eq("employee_id", employee_id)
    return query.execute().data or []


def fetch_exceptions(date_from=None, date_to=None, employee_id: str | None = None) -> list[dict[str, Any]]:
    query = client().table("exceptions").select("*").order("date_from", desc=True)
    if date_to is not None:
        query = query.lte("date_from", str(date_to))
    if date_from is not None:
        query = query.gte("date_to", str(date_from))
    if employee_id:
        query = query.eq("employee_id", employee_id)
    return query.execute().data or []


def fetch_holidays(date_from=None, date_to=None) -> list[dict[str, Any]]:
    query = client().table("holidays").select("*").order("date")
    if date_from is not None:
        query = query.gte("date", str(date_from))
    if date_to is not None:
        query = query.lte("date", str(date_to))
    return query.execute().data or []


def fetch_correction_requests(status: str | None = None) -> list[dict[str, Any]]:
    query = client().table("correction_requests").select("*").order("created_at", desc=True)
    if status:
        query = query.eq("status", status)
    return query.execute().data or []


def log_action(actor_id: str | None, actor_name: str | None, action: str,
               entity: str, entity_id: str | None = None, details: dict | None = None) -> None:
    try:
        client().table("audit_log").insert({
            "actor_id": actor_id,
            "actor_name": actor_name,
            "action": action,
            "entity": entity,
            "entity_id": entity_id,
            "details": details or {},
        }).execute()
    except Exception:
        pass  # la bitácora nunca debe romper una operación del usuario
