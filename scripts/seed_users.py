"""
Crea los usuarios iniciales en Supabase (Auth + tabla employees).

Cómo usarlo
-----------
1. Edita la lista EMPLEADOS de abajo: correo real, fecha de nacimiento y cargo.
2. Exporta las credenciales del proyecto (Supabase → Project Settings → API):

       export SUPABASE_URL="https://xxxxxxxx.supabase.co"
       export SUPABASE_SERVICE_KEY="eyJ...la clave service_role..."

3. Ejecuta:

       pip install supabase
       python scripts/seed_users.py

El script es idempotente: si el usuario ya existe, actualiza su perfil
en lugar de fallar. Las contraseñas temporales se imprimen al final;
entrégalas a cada persona y pídeles cambiarla desde "Mi perfil".

IMPORTANTE: la clave service_role da acceso total a la base de datos.
Úsala solo desde tu computadora y nunca la subas a GitHub.
"""

from __future__ import annotations

import os
import secrets
import string
import sys

try:
    from supabase import create_client
except ImportError:  # pragma: no cover
    sys.exit("Falta la librería. Ejecuta:  pip install supabase")


# ---------------------------------------------------------------------
# EDITA ESTA LISTA ANTES DE EJECUTAR
# ---------------------------------------------------------------------
# birth_date en formato AAAA-MM-DD. Déjalo en None si aún no lo tienes:
# Keren puede completarlo después desde el panel de Empleados.
EMPLEADOS = [
    {
        "full_name":  "Keren Orozco",
        "email":      "CAMBIAR-keren@ejemplo.com",     # <-- correo real
        "role":       "admin",
        "position":   "Gerente de Recursos Humanos",
        "birth_date": "1991-12-28",
        "shift_start": "07:00",
        "shift_end":   "16:00",
    },
    {
        "full_name":  "Edgar Dávila",
        "email":      "CAMBIAR-edgar@ejemplo.com",
        "role":       "employee",
        "position":   None,
        "birth_date": None,
        "shift_start": "09:00",
        "shift_end":   "18:00",
    },
    {
        "full_name":  "Eddie Bustamante",
        "email":      "CAMBIAR-eddie@ejemplo.com",
        "role":       "employee",
        "position":   None,
        "birth_date": None,
        "shift_start": "07:30",
        "shift_end":   "16:30",
    },
    {
        "full_name":  "Ellie Gonzáles",
        "email":      "CAMBIAR-ellie@ejemplo.com",
        "role":       "employee",
        "position":   None,
        "birth_date": None,
        "shift_start": "10:00",
        "shift_end":   "19:00",
    },
    {
        "full_name":  "José Izquierdo",
        "email":      "CAMBIAR-jose@ejemplo.com",
        "role":       "employee",
        "position":   None,
        "birth_date": None,
        "shift_start": "10:00",
        "shift_end":   "15:00",
    },
]

# Parámetros comunes
LUNCH_THRESHOLD_HOURS = 6.0   # solo se descuenta almuerzo si la jornada supera 6 h
LUNCH_DEDUCTION_MIN = 60
GRACE_MINUTES = 15
WORK_DAYS = [1, 2, 3, 4, 5]   # lunes a viernes


def generar_password(largo: int = 12) -> str:
    alfabeto = string.ascii_letters + string.digits
    return "Rdp" + "".join(secrets.choice(alfabeto) for _ in range(largo))


def main() -> None:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        sys.exit("Faltan las variables SUPABASE_URL y SUPABASE_SERVICE_KEY.")

    pendientes = [e for e in EMPLEADOS if e["email"].startswith("CAMBIAR-")]
    if pendientes:
        nombres = ", ".join(e["full_name"] for e in pendientes)
        sys.exit(f"Todavía hay correos de ejemplo sin cambiar: {nombres}")

    sb = create_client(url, key)
    credenciales: list[tuple[str, str, str]] = []

    # Usuarios ya existentes en Auth
    existentes = {}
    page = 1
    while True:
        lote = sb.auth.admin.list_users(page=page, per_page=100)
        usuarios = lote if isinstance(lote, list) else getattr(lote, "users", [])
        if not usuarios:
            break
        for u in usuarios:
            if u.email:
                existentes[u.email.lower()] = u.id
        page += 1

    for emp in EMPLEADOS:
        email = emp["email"].strip().lower()
        uid = existentes.get(email)
        password = ""

        if uid is None:
            password = generar_password()
            creado = sb.auth.admin.create_user({
                "email": email,
                "password": password,
                "email_confirm": True,
                "user_metadata": {"full_name": emp["full_name"]},
            })
            uid = creado.user.id
            credenciales.append((emp["full_name"], email, password))
            print(f"  + Usuario creado: {emp['full_name']}")
        else:
            print(f"  = Usuario ya existía: {emp['full_name']}")

        perfil = {
            "id": uid,
            "full_name": emp["full_name"],
            "email": email,
            "role": emp["role"],
            "position": emp["position"],
            "birth_date": emp["birth_date"],
            "shift_start": emp["shift_start"],
            "shift_end": emp["shift_end"],
            "work_days": WORK_DAYS,
            "lunch_threshold_hours": LUNCH_THRESHOLD_HOURS,
            "lunch_deduction_minutes": LUNCH_DEDUCTION_MIN,
            "grace_minutes": GRACE_MINUTES,
            "is_active": True,
        }
        sb.table("employees").upsert(perfil, on_conflict="id").execute()
        print(f"    perfil guardado ({emp['shift_start']} – {emp['shift_end']})")

    print("\nListo.")
    if credenciales:
        print("\nContraseñas temporales — entrégalas de forma segura:\n")
        for nombre, email, pwd in credenciales:
            print(f"  {nombre:<22} {email:<32} {pwd}")
        print("\nPídeles cambiarla en la app: menú → Mi perfil → Cambiar contraseña.")


if __name__ == "__main__":
    main()
