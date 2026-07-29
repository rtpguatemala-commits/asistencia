"""Pantalla principal del empleado: marcar entrada y salida."""

from __future__ import annotations

from typing import Any

import streamlit as st

from .. import analytics, auth, db, geo, theme
from ..config import COLORS
from ..tz import (
    day_name,
    fmt_date,
    fmt_time,
    minutes_to_hhmm,
    now_gt,
    parse_time,
    today_gt,
    to_gt,
)


def _today_record(user_id: str) -> dict[str, Any] | None:
    today = today_gt()
    rows = (
        db.client().table("attendance").select("*")
        .eq("employee_id", user_id).eq("work_date", str(today))
        .limit(1).execute().data or []
    )
    return rows[0] if rows else None


def _open_record(user_id: str) -> dict[str, Any] | None:
    rows = (
        db.client().table("attendance").select("*")
        .eq("employee_id", user_id).is_("clock_out_at", "null")
        .not_.is_("clock_in_at", "null")
        .order("work_date", desc=True).limit(1).execute().data or []
    )
    return rows[0] if rows else None


@st.fragment(run_every="30s")
def _live_clock() -> None:
    now = now_gt()
    st.markdown(
        f"""
<div class="rdp-clock">
  <div class="hh">{now.strftime('%H:%M')}</div>
  <div class="dd">{day_name(now.date())}, {fmt_date(now.date())}</div>
  <div class="tzz">Hora de Guatemala (UTC−6)</div>
</div>
""",
        unsafe_allow_html=True,
    )


def _schedule_banner(profile: dict[str, Any]) -> None:
    start = parse_time(profile.get("shift_start"))
    end = parse_time(profile.get("shift_end"))
    grace = int(profile.get("grace_minutes") or 15)
    exp = analytics.expected_minutes(profile)
    st.markdown(
        theme.note(
            f"Tu horario es de <b>{start.strftime('%H:%M') if start else '—'}</b> a "
            f"<b>{end.strftime('%H:%M') if end else '—'}</b>, "
            f"con <b>{grace} minutos</b> de tolerancia. "
            f"Jornada esperada: <b>{minutes_to_hhmm(exp)}</b> netas.",
            "info",
        ),
        unsafe_allow_html=True,
    )


def _location_panel(mode: str, settings: dict[str, Any], slot: str) -> dict[str, Any]:
    """Muestra el estado del GPS y devuelve la evaluación de la geocerca."""
    location = geo.cached_location(f"geo_{slot}")
    evaluation = geo.evaluate(location, settings)

    if not geo.JS_EVAL_OK:
        st.warning(
            "El componente de ubicación no está instalado. "
            "Agrega `streamlit-js-eval` a requirements.txt."
        )
        return evaluation

    if mode == "building":
        if location is None:
            st.markdown(
                theme.note(
                    "Buscando tu ubicación… Si el navegador te pregunta, "
                    "toca <b>Permitir</b>. En iPhone debe estar activado "
                    "Ajustes → Safari → Ubicación.",
                    "info",
                ),
                unsafe_allow_html=True,
            )
        elif evaluation["ok"]:
            st.markdown(theme.note("✓ " + evaluation["message"], "ok"), unsafe_allow_html=True)
        else:
            st.markdown(theme.note("✕ " + evaluation["message"], "error"), unsafe_allow_html=True)

        if location:
            st.caption(
                f"Precisión reportada por tu dispositivo: ± {location['accuracy']:.0f} m · "
                f"Radio permitido: {evaluation['radius']:.0f} m"
            )
    else:
        if location:
            st.caption(
                f"Se guardará tu ubicación actual "
                f"(a {evaluation['distance']:.0f} m del edificio) junto con el motivo."
                if evaluation["distance"] is not None else
                "Se guardará tu ubicación actual junto con el motivo."
            )
        else:
            st.caption("Si autorizas la ubicación, se guardará junto con el motivo.")

    return evaluation


def _do_clock(action: str, mode: str, location: dict[str, Any] | None, reason: str) -> None:
    payload = {
        "p_mode": mode,
        "p_lat": location["lat"] if location else None,
        "p_lng": location["lng"] if location else None,
        "p_accuracy": location["accuracy"] if location else None,
        "p_reason": reason or None,
    }
    try:
        db.client().rpc(action, payload).execute()
        st.session_state["clock_feedback"] = (
            "ok",
            "Entrada registrada. ¡Buen día!" if action == "clock_in"
            else "Salida registrada. ¡Gracias por tu jornada!",
        )
    except Exception as exc:
        st.session_state["clock_feedback"] = ("error", db.error_message(exc))
    st.rerun()


def render() -> None:
    profile = auth.current_profile()
    user_id = auth.current_user_id()
    settings = db.fetch_settings()

    feedback = st.session_state.pop("clock_feedback", None)
    if feedback:
        kind, message = feedback
        (st.success if kind == "ok" else st.error)(message)

    col_left, col_right = st.columns([1, 1], gap="large")

    with col_left:
        _live_clock()
        st.write("")
        _schedule_banner(profile)

    record = _today_record(user_id)
    open_record = _open_record(user_id)
    # Una jornada abierta de un día anterior también permite marcar salida.
    active = record if (record and record.get("clock_in_at") and not record.get("clock_out_at")) else open_record

    with col_right:
        # ------------- Estado de hoy -------------
        clock_in = to_gt(record.get("clock_in_at")) if record else None
        clock_out = to_gt(record.get("clock_out_at")) if record else None

        theme.card_open("Tu jornada de hoy")
        c1, c2, c3 = st.columns(3)
        c1.markdown(theme.stat("Entrada", fmt_time(clock_in)), unsafe_allow_html=True)
        c2.markdown(theme.stat("Salida", fmt_time(clock_out)), unsafe_allow_html=True)
        net = record.get("net_minutes") if record else None
        c3.markdown(
            theme.stat("Horas netas", minutes_to_hhmm(net) if net is not None else "—"),
            unsafe_allow_html=True,
        )
        if record:
            st.markdown(theme.badge(record.get("status", "open")), unsafe_allow_html=True)
            if record.get("late_minutes"):
                st.caption(f"Retraso registrado: {record['late_minutes']} minutos.")
            if record.get("clock_in_reason"):
                st.caption(f"Motivo de ubicación: {record['clock_in_reason']}")
        theme.card_close()

        if active and active.get("work_date") != str(today_gt()):
            st.warning(
                f"Tienes una jornada abierta del {active['work_date']}. "
                "Márcala como terminada o solicita una corrección a la gerencia."
            )

        # ------------- Acción -------------
        if record and record.get("clock_in_at") and record.get("clock_out_at"):
            st.markdown(
                theme.note("Ya completaste tu jornada de hoy. Que descanses.", "ok"),
                unsafe_allow_html=True,
            )
            return

        accion = "clock_out" if active else "clock_in"
        etiqueta = "Terminar Jornada" if active else "Empezar Jornada"
        slot = "out" if active else "in"

        theme.card_open(etiqueta)
        mode_label = st.radio(
            "¿Desde dónde marcas?",
            ["En el Edificio", "Otro lugar"],
            horizontal=True,
            key=f"mode_{slot}",
        )
        mode = "building" if mode_label == "En el Edificio" else "other"

        reason = ""
        if mode == "other":
            reason = st.text_input(
                "Motivo (obligatorio)",
                key=f"reason_{slot}",
                placeholder="Visita de campo en Chimaltenango, trabajo desde casa, etc.",
                max_chars=200,
            )

        evaluation = _location_panel(mode, settings, slot)
        location = st.session_state.get("geo")

        puede = True
        aviso = ""
        if mode == "building":
            if location is None:
                puede, aviso = False, "Esperando la ubicación de tu dispositivo."
            elif not evaluation["ok"]:
                puede, aviso = False, evaluation["message"]
        else:
            if len(reason.strip()) < 5:
                puede, aviso = False, "Escribe el motivo (mínimo 5 caracteres)."

        if st.button(etiqueta, type="primary", width="stretch",
                     disabled=not puede, key=f"btn_{slot}"):
            _do_clock(accion, mode, location, reason)

        if not puede and aviso:
            st.caption(aviso)

        if mode == "building":
            if st.button("Volver a intentar la ubicación", width="stretch",
                         key=f"retry_{slot}"):
                st.session_state.pop("geo", None)
                st.rerun()

        theme.card_close()
