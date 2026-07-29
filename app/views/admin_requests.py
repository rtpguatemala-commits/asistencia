"""Solicitudes de corrección enviadas por los empleados."""

from __future__ import annotations

from datetime import date

import streamlit as st

from .. import auth, db, theme
from ..config import COLORS
from ..tz import fmt_date, fmt_datetime, fmt_date_short, now_gt, to_gt


def _card(req: dict, nombre: str) -> None:
    entrada = to_gt(req.get("requested_clock_in"))
    salida = to_gt(req.get("requested_clock_out"))

    st.markdown(
        f"""
<div class="rdp-card">
  <div style="font-weight:700">{nombre}</div>
  <div style="font-size:.8rem;color:{COLORS['muted']};margin-bottom:.5rem">
    Día {fmt_date_short(date.fromisoformat(req['work_date']))} ·
    enviada el {fmt_date_short(to_gt(req['created_at']).date()) if to_gt(req['created_at']) else '—'}
  </div>
  <div style="font-size:.9rem">
    Entrada solicitada: <b>{entrada.strftime('%H:%M') if entrada else '—'}</b> ·
    Salida solicitada: <b>{salida.strftime('%H:%M') if salida else '—'}</b>
  </div>
  <div style="font-size:.87rem;color:{COLORS['muted']};margin-top:.4rem">
    "{req.get('reason', '')}"
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    nota = st.text_input("Comentario para la persona (opcional)", key=f"note_{req['id']}")
    c1, c2 = st.columns(2)
    if c1.button("Aprobar y corregir", type="primary", width="stretch",
                 key=f"ok_{req['id']}"):
        try:
            db.client().rpc("approve_correction", {
                "p_request_id": req["id"],
                "p_review_note": nota or None,
            }).execute()
            st.success("Solicitud aprobada y registro corregido.")
            st.rerun()
        except Exception as exc:
            st.error(db.error_message(exc))

    if c2.button("Rechazar", width="stretch", key=f"no_{req['id']}"):
        try:
            db.client().table("correction_requests").update({
                "status": "rejected",
                "reviewed_by": auth.current_user_id(),
                "reviewed_at": now_gt().isoformat(),
                "review_note": nota or None,
            }).eq("id", req["id"]).execute()
            st.success("Solicitud rechazada.")
            st.rerun()
        except Exception as exc:
            st.error(db.error_message(exc))


def render() -> None:
    if not auth.require_admin():
        return

    employees = db.fetch_employees(include_inactive=True)
    mapa = {e["id"]: e["full_name"] for e in employees}

    pendientes = db.fetch_correction_requests(status="pending")
    historial = [r for r in db.fetch_correction_requests() if r["status"] != "pending"]

    st.markdown(f"#### Pendientes ({len(pendientes)})")
    if not pendientes:
        st.markdown(theme.note("No hay solicitudes pendientes.", "ok"), unsafe_allow_html=True)
    for req in pendientes:
        _card(req, mapa.get(req["employee_id"], "—"))
        st.divider()

    with st.expander(f"Historial ({len(historial)})"):
        for req in historial[:50]:
            estado = "Aprobada" if req["status"] == "approved" else "Rechazada"
            color = COLORS["success"] if req["status"] == "approved" else COLORS["danger"]
            st.markdown(
                f'- **{mapa.get(req["employee_id"], "—")}** · '
                f'{fmt_date_short(date.fromisoformat(req["work_date"]))} · '
                f'<span style="color:{color}">{estado}</span>'
                + (f' · _{req.get("review_note")}_' if req.get("review_note") else ""),
                unsafe_allow_html=True,
            )
