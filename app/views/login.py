"""Pantalla de inicio de sesión."""

from __future__ import annotations

import streamlit as st

from .. import auth, db, theme
from ..config import COLORS, ORG_NAME
from ..tz import fmt_date, now_gt


def render() -> None:
    theme.inject_css()

    left, center, right = st.columns([1, 1.35, 1])
    with center:
        logo = theme.logo_data_uri()
        st.markdown(
            f"""
<div style="text-align:center;padding:1.6rem 0 .6rem">
  {'<img src="' + logo + '" style="width:104px;height:104px;border-radius:26px">' if logo else ''}
  <div style="font-size:1.28rem;font-weight:800;margin-top:.85rem;color:{COLORS['text']}">
    {ORG_NAME}
  </div>
  <div style="font-size:.9rem;color:{COLORS['muted']};margin-top:.15rem">
    Control de Asistencia
  </div>
  <div style="font-size:.76rem;color:{COLORS['muted']};opacity:.7;margin-top:.5rem">
    {fmt_date(now_gt().date())} · {now_gt().strftime('%H:%M')} hora de Guatemala
  </div>
</div>
""",
            unsafe_allow_html=True,
        )

        if not db.secrets_ok():
            st.error(
                "La aplicación no tiene configuradas las credenciales de Supabase. "
                "Agrega SUPABASE_URL y SUPABASE_ANON_KEY en los secretos de la app."
            )
            return

        with st.form("form_login", clear_on_submit=False):
            email = st.text_input("Correo electrónico", placeholder="nombre@organizacion.org")
            password = st.text_input("Contraseña", type="password", placeholder="••••••••")
            submitted = st.form_submit_button("Ingresar", type="primary", width="stretch")

        if submitted:
            if not email or not password:
                st.warning("Escribe tu correo y tu contraseña.")
            else:
                with st.spinner("Verificando…"):
                    ok, message = auth.sign_in(email, password)
                if ok:
                    st.rerun()
                else:
                    st.error(message)

        with st.expander("Olvidé mi contraseña"):
            reset_email = st.text_input("Tu correo", key="reset_email",
                                        placeholder="nombre@organizacion.org")
            if st.button("Enviarme el enlace", width="stretch"):
                if not reset_email:
                    st.warning("Escribe tu correo.")
                else:
                    ok, message = auth.send_password_reset(reset_email)
                    (st.success if ok else st.error)(message)

        st.markdown(
            f"""
<div style="text-align:center;font-size:.74rem;color:{COLORS['muted']};
            opacity:.6;margin-top:1.6rem;line-height:1.6">
  ¿No tienes cuenta? Solicítala a la gerencia de Recursos Humanos.<br>
  Consejo: agrega esta página a la pantalla de inicio de tu teléfono
  para abrirla como aplicación.
</div>
""",
            unsafe_allow_html=True,
        )
