"""Perfil personal y cambio de contraseña."""

from __future__ import annotations

import streamlit as st

from .. import analytics, auth, theme
from ..config import COLORS, DAY_NAMES
from ..tz import fmt_date, minutes_to_hhmm, parse_date, parse_time


def render() -> None:
    profile = auth.current_profile()

    left, right = st.columns([1, 1], gap="large")

    with left:
        theme.card_open("Mis datos")
        start = parse_time(profile.get("shift_start"))
        end = parse_time(profile.get("shift_end"))
        dias = ", ".join(DAY_NAMES[d] for d in sorted(profile.get("work_days") or []))
        st.markdown(
            f"""
- **Nombre:** {profile.get('full_name', '—')}
- **Correo:** {profile.get('email', '—')}
- **Cargo:** {profile.get('position') or '—'}
- **Rol:** {'Gerencia' if profile.get('role') == 'admin' else 'Colaborador'}
- **Horario:** {start.strftime('%H:%M') if start else '—'} a {end.strftime('%H:%M') if end else '—'}
- **Días:** {dias or '—'}
- **Tolerancia:** {profile.get('grace_minutes', 15)} minutos
- **Jornada esperada:** {minutes_to_hhmm(analytics.expected_minutes(profile))} netas
- **Fecha de nacimiento:** {fmt_date(parse_date(profile.get('birth_date'))) if profile.get('birth_date') else '—'}
"""
        )
        st.caption(
            "Si algún dato está mal, pídele a la gerencia que lo corrija "
            "en la sección Empleados."
        )
        theme.card_close()

    with right:
        theme.card_open("Cambiar mi contraseña")
        with st.form("form_password"):
            nueva = st.text_input("Nueva contraseña", type="password")
            repetir = st.text_input("Repetir contraseña", type="password")
            enviar = st.form_submit_button("Actualizar", type="primary", width="stretch")
        if enviar:
            if len(nueva) < 8:
                st.warning("La contraseña debe tener al menos 8 caracteres.")
            elif nueva != repetir:
                st.warning("Las dos contraseñas no coinciden.")
            else:
                ok, mensaje = auth.change_password(nueva)
                (st.success if ok else st.error)(mensaje)
        theme.card_close()

        theme.card_open("Instalar la app en el teléfono")
        st.markdown(
            """
**Android (Chrome)**
1. Abre esta página en Chrome.
2. Toca el menú ⋮ y elige *Agregar a pantalla principal*.

**iPhone (Safari)**
1. Abre esta página en Safari.
2. Toca el botón de compartir y elige *Agregar a inicio*.

Quedará con el ícono de la organización y se abrirá a pantalla completa.
"""
        )
        theme.card_close()
