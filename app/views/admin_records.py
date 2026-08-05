"""Todos los registros de asistencia, con filtros y edición manual."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from .. import analytics, auth, db, theme
from ..config import COLORS, EXCEPTION_LABELS, QUICK_EXCEPTION_TYPES, STATUS_LABELS
from ..tz import (
    combine_gt,
    fmt_date_short,
    gt_to_utc_iso,
    hhmm,
    minutes_to_hhmm,
    now_gt,
    parse_date,
    today_gt,
    to_gt,
)
from .history import _range_picker, detail_table


def _editor(employees: list[dict]) -> None:
    st.markdown("Corrige manualmente un registro. Todo cambio queda en la bitácora.")
    mapa = {e["full_name"]: e["id"] for e in employees}
    nombre = st.selectbox("Empleado", list(mapa.keys()), key="edit_emp")
    dia = st.date_input("Fecha", key="edit_date", format="DD/MM/YYYY")

    emp_id = mapa[nombre]
    existente = (
        db.client().table("attendance").select("*")
        .eq("employee_id", emp_id).eq("work_date", str(dia)).limit(1).execute().data or []
    )
    registro = existente[0] if existente else None

    if registro:
        ent = to_gt(registro.get("clock_in_at"))
        sal = to_gt(registro.get("clock_out_at"))
        st.caption(
            f"Registro actual: entrada {ent.strftime('%H:%M') if ent else '—'}, "
            f"salida {sal.strftime('%H:%M') if sal else '—'}, "
            f"estado {STATUS_LABELS.get(registro.get('status'), '—')}."
        )
    else:
        st.caption("No hay registro para esa fecha. Se creará uno nuevo.")
        ent = sal = None

    cols = st.columns(2)
    hora_in = cols[0].time_input("Entrada", value=ent.time() if ent else None, key="edit_in")
    hora_out = cols[1].time_input("Salida", value=sal.time() if sal else None, key="edit_out")
    nota = st.text_input("Observación", value=(registro or {}).get("note") or "", key="edit_note")

    b1, b2 = st.columns(2)
    if b1.button("Guardar registro", type="primary", width="stretch"):
        payload = {
            "employee_id": emp_id,
            "work_date": str(dia),
            "clock_in_at": gt_to_utc_iso(combine_gt(dia, hora_in)) if hora_in else None,
            "clock_out_at": gt_to_utc_iso(combine_gt(dia, hora_out)) if hora_out else None,
            "note": nota or None,
            "needs_review": False,
            "auto_closed": False,
            "edited_by": auth.current_user_id(),
            "edited_at": gt_to_utc_iso(now_gt()),
        }
        try:
            db.client().table("attendance").upsert(
                payload, on_conflict="employee_id,work_date"
            ).execute()
            db.log_action(auth.current_user_id(), auth.current_profile().get("full_name"),
                          "edit_attendance", "attendance", None,
                          {"employee": nombre, "date": str(dia)})
            st.success("Registro guardado.")
            st.rerun()
        except Exception as exc:
            st.error(db.error_message(exc))

    if registro and b2.button("Eliminar registro", width="stretch"):
        try:
            db.client().table("attendance").delete().eq("id", registro["id"]).execute()
            db.log_action(auth.current_user_id(), auth.current_profile().get("full_name"),
                          "delete_attendance", "attendance", registro["id"],
                          {"employee": nombre, "date": str(dia)})
            st.success("Registro eliminado.")
            st.rerun()
        except Exception as exc:
            st.error(db.error_message(exc))


def justificar(grid: pd.DataFrame) -> None:
    """Marca un día suelto como justificado: tardanza permitida, salida
    anticipada autorizada, ausencia con permiso, etc."""
    st.markdown(
        "Si alguien llegó tarde con permiso, se retiró antes por una razón válida "
        "o faltó de forma justificada, márcalo aquí. El día deja de contar como "
        "incidencia y queda con la nota que escribas."
    )

    aviso = st.session_state.pop("just_feedback", None)
    if aviso:
        tipo_aviso, texto = aviso
        (st.success if tipo_aviso == "ok" else st.error)(texto)

    hoy = today_gt()
    incidencias = analytics.incidents(grid)
    incidencias = incidencias[incidencias["estado"].isin(
        ["late", "early_leave", "late_and_early", "absent", "open"]
    )]
    # Un día que todavía está en curso no es una incidencia: puede que la
    # persona siga trabajando o que aún no le toque marcar.
    incidencias = incidencias[
        ~((incidencias["fecha"] == hoy) & incidencias["estado"].isin(["open", "absent"]))
    ].sort_values(["fecha", "empleado"], ascending=[False, True])

    if incidencias.empty:
        st.markdown(
            theme.note("No hay días con incidencia en el período seleccionado.", "ok"),
            unsafe_allow_html=True,
        )
        return

    st.markdown(f"**Días con incidencia en el período: {len(incidencias)}**")
    resumen_inc = pd.DataFrame({
        "Empleado": incidencias["empleado"],
        "Fecha": incidencias["fecha"].apply(fmt_date_short),
        "Día": incidencias["dia"],
        "Entrada": incidencias["entrada"].apply(hhmm),
        "Salida": incidencias["salida"].apply(hhmm),
        "Estado": incidencias["estado_texto"],
        "Retraso": incidencias["tarde_min"].apply(lambda m: f"{int(m)} min" if m else "—"),
        "Salió antes": incidencias["temprano_min"].apply(lambda m: f"{int(m)} min" if m else "—"),
    })
    st.dataframe(resumen_inc, width="stretch", hide_index=True, height=260)

    opciones = {
        f"{r['empleado']} · {fmt_date_short(r['fecha'])} ({r['dia']}) · {r['estado_texto']}":
            (r["employee_id"], r["fecha"], r["estado"])
        for _, r in incidencias.iterrows()
    }

    st.write("")
    elegido = st.selectbox("Día a justificar", list(opciones.keys()), key="just_pick")
    emp_id, dia, estado = opciones[elegido]

    # Sugerencia de tipo según lo que pasó ese día
    sugerido = {
        "early_leave": "early_leave_ok",
        "late": "justified_late",
        "late_and_early": "early_leave_ok",
        "absent": "absence_ok",
        "open": "absence_ok",
    }.get(estado, "personal_leave")

    c1, c2 = st.columns([1.2, 1])
    tipo = c1.selectbox(
        "Tipo de justificación",
        QUICK_EXCEPTION_TYPES,
        index=QUICK_EXCEPTION_TYPES.index(sugerido) if sugerido in QUICK_EXCEPTION_TYPES else 0,
        format_func=lambda t: EXCEPTION_LABELS.get(t, t),
        key="just_type",
    )
    pagado = c2.checkbox(
        "Cuenta como horas pagadas", value=True, key="just_paid",
        help="Si lo desmarcas, ese día no suma a las horas acreditadas del reporte.",
    )
    nota = st.text_area(
        "Nota para el expediente",
        key="just_note",
        max_chars=400,
        placeholder="Ejemplo: Se retiró a las 14:00 con autorización para asistir a una cita "
                    "médica. Presentó constancia.",
    )

    if st.button("Justificar este día", type="primary", width="stretch"):
        if len(nota.strip()) < 5:
            st.warning("Escribe una nota breve explicando la justificación.")
            return
        try:
            db.client().rpc("justify_day", {
                "p_employee_id": emp_id,
                "p_date": str(dia),
                "p_type": tipo,
                "p_note": nota.strip(),
                "p_paid": bool(pagado),
            }).execute()
            st.session_state["just_feedback"] = (
                "ok",
                f"Día justificado como «{EXCEPTION_LABELS.get(tipo, tipo)}». "
                "Ya no aparece como incidencia.",
            )
            st.rerun()
        except Exception as exc:
            st.session_state["just_feedback"] = ("error", db.error_message(exc))
            st.rerun()


def render() -> None:
    if not auth.require_admin():
        return

    employees = db.fetch_employees(include_inactive=True)
    if not employees:
        st.info("Todavía no hay empleados registrados.")
        return

    start, end = _range_picker("adm")

    nombres = ["Todos"] + [e["full_name"] for e in employees]
    filtro_emp = st.multiselect("Empleados", nombres, default=["Todos"], key="adm_emp")
    filtro_estado = st.multiselect(
        "Estado",
        [STATUS_LABELS[k] for k in
         ("on_time", "late", "early_leave", "late_and_early", "open", "absent",
          "exception", "holiday", "rest")],
        key="adm_status",
    )

    seleccionados = (
        employees if ("Todos" in filtro_emp or not filtro_emp)
        else [e for e in employees if e["full_name"] in filtro_emp]
    )

    attendance = db.fetch_attendance(start, end)
    exceptions = db.fetch_exceptions(start, end)
    holidays = db.fetch_holidays(start, end)
    grid = analytics.build_grid(seleccionados, attendance, exceptions, holidays, start, end)

    if grid.empty:
        st.info("No hay datos en el período seleccionado.")
        return

    if filtro_estado:
        grid = grid[grid["estado_texto"].isin(filtro_estado)]

    resumen = analytics.summarize(grid)

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(theme.stat("Registros", str(len(grid))), unsafe_allow_html=True)
    c2.markdown(theme.stat("Horas trabajadas", minutes_to_hhmm(grid["neto_min"].sum())),
                unsafe_allow_html=True)
    c3.markdown(theme.stat("Tardanzas",
                           str(int(grid["estado"].isin(["late", "late_and_early"]).sum())),
                           color=COLORS["warning"]), unsafe_allow_html=True)
    c4.markdown(theme.stat("Ausencias", str(int((grid["estado"] == "absent").sum())),
                           color=COLORS["danger"]), unsafe_allow_html=True)

    st.write("")
    tab1, tab2, tab3, tab4 = st.tabs(
        ["Detalle", "Justificar un día", "Resumen por empleado", "Corregir un registro"]
    )

    with tab1:
        ordenado = grid.sort_values(["fecha", "empleado"], ascending=[False, True])
        vista = detail_table(ordenado)
        vista.insert(0, "Empleado", ordenado["empleado"].values)
        st.dataframe(vista, width="stretch", hide_index=True, height=520)

    with tab2:
        justificar(grid)

    with tab3:
        if resumen.empty:
            st.info("Sin datos.")
        else:
            st.dataframe(
                resumen.drop(columns=["employee_id"]),
                width="stretch", hide_index=True,
            )

    with tab4:
        _editor(employees)
