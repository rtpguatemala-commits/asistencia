"""Construcción de la malla diaria de asistencia y sus resúmenes."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pandas as pd

from .config import EXCEPTION_LABELS, STATUS_LABELS
from .tz import (
    combine_gt,
    date_range,
    day_name,
    parse_date,
    parse_time,
    to_gt,
    today_gt,
)


def expected_minutes(employee: dict[str, Any]) -> int:
    """Minutos netos que se esperan de un empleado en un día laboral."""
    start = parse_time(employee.get("shift_start"))
    end = parse_time(employee.get("shift_end"))
    if start is None or end is None:
        return 0
    gross = (end.hour * 60 + end.minute) - (start.hour * 60 + start.minute)
    if gross <= 0:
        gross += 24 * 60
    threshold = float(employee.get("lunch_threshold_hours") or 6) * 60
    deduction = int(employee.get("lunch_deduction_minutes") or 0)
    lunch = deduction if gross > threshold else 0
    return max(0, gross - min(lunch, gross))


def schedule_label(employee: dict[str, Any]) -> str:
    start = parse_time(employee.get("shift_start"))
    end = parse_time(employee.get("shift_end"))
    if start is None or end is None:
        return "—"
    return f"{start.strftime('%H:%M')} – {end.strftime('%H:%M')}"


def _index_exceptions(exceptions: list[dict[str, Any]]) -> dict[tuple[str, date], dict]:
    index: dict[tuple[str, date], dict] = {}
    for ex in exceptions:
        start = parse_date(ex.get("date_from"))
        end = parse_date(ex.get("date_to"))
        if start is None or end is None:
            continue
        for day in date_range(start, end):
            index[(ex["employee_id"], day)] = ex
    return index


def build_grid(
    employees: list[dict[str, Any]],
    attendance: list[dict[str, Any]],
    exceptions: list[dict[str, Any]],
    holidays: list[dict[str, Any]],
    date_from: date,
    date_to: date,
) -> pd.DataFrame:
    """Una fila por empleado y por día dentro del rango, incluyendo ausencias."""
    att_index = {(a["employee_id"], parse_date(a["work_date"])): a for a in attendance}
    exc_index = _index_exceptions(exceptions)
    hol_index = {parse_date(h["date"]): h for h in holidays}
    today = today_gt()

    rows: list[dict[str, Any]] = []
    for emp in employees:
        emp_id = emp["id"]
        work_days = set(emp.get("work_days") or [1, 2, 3, 4, 5])
        exp_min = expected_minutes(emp)
        sched = schedule_label(emp)

        for day in date_range(date_from, date_to):
            iso_dow = day.isoweekday()
            att = att_index.get((emp_id, day))
            exc = exc_index.get((emp_id, day))
            hol = hol_index.get(day)
            is_workday = iso_dow in work_days

            clock_in = to_gt(att.get("clock_in_at")) if att else None
            clock_out = to_gt(att.get("clock_out_at")) if att else None
            net = att.get("net_minutes") if att else None
            net = int(net) if net is not None else 0

            # ---- Estado del día ----
            if not is_workday:
                status = "rest"
                expected = 0
            elif hol is not None and att is None:
                status = "holiday"
                expected = 0
            elif att is not None:
                status = att.get("status") or "open"
                expected = exp_min if hol is None else 0
                # Si la gerencia justificó el día, deja de contar como incidencia
                if exc is not None and status in (
                    "late", "early_leave", "late_and_early", "absent"
                ):
                    status = "exception"
            elif exc is not None:
                status = "exception"
                expected = 0
            elif day >= today:
                # El día de hoy todavía está en curso: no es una ausencia
                status = "future"
                expected = exp_min
            else:
                status = "absent"
                expected = exp_min

            # ---- Minutos acreditados (trabajados + justificados pagados) ----
            credited = net
            if att is None:
                if hol is not None and is_workday:
                    credited = exp_min
                elif exc is not None and exc.get("counts_as_paid", True) and is_workday:
                    credited = exp_min

            rows.append({
                "employee_id": emp_id,
                "empleado": emp.get("full_name", ""),
                "cargo": emp.get("position") or "",
                "fecha": day,
                "dia": day_name(day),
                "horario": sched if is_workday else "—",
                "laboral": is_workday,
                "asueto": hol.get("name") if hol else "",
                "excepcion": EXCEPTION_LABELS.get(exc.get("type"), "") if exc else "",
                "excepcion_nota": (exc.get("note") or "") if exc else "",
                "entrada": clock_in,
                "salida": clock_out,
                "modo_entrada": (att.get("clock_in_mode") or "") if att else "",
                "modo_salida": (att.get("clock_out_mode") or "") if att else "",
                "motivo_ubicacion": (att.get("clock_in_reason") or "") if att else "",
                "distancia_m": (att.get("clock_in_distance_m") if att else None),
                "bruto_min": (att.get("gross_minutes") or 0) if att else 0,
                "almuerzo_min": (att.get("lunch_minutes") or 0) if att else 0,
                "neto_min": net,
                "acreditado_min": credited,
                "esperado_min": expected,
                "tarde_min": (att.get("late_minutes") or 0) if att else 0,
                "temprano_min": (att.get("early_leave_minutes") or 0) if att else 0,
                "extra_min": (att.get("overtime_minutes") or 0) if att else 0,
                "estado": status,
                "estado_texto": STATUS_LABELS.get(status, status),
                "revisar": bool(att.get("needs_review")) if att else False,
                "auto": bool(att.get("auto_closed")) if att else False,
                "observacion": (att.get("note") or "") if att else "",
                "bitacora": (att.get("work_summary") or "") if att else "",
                "attendance_id": att.get("id") if att else None,
            })

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values(["empleado", "fecha"]).reset_index(drop=True)
    return df


def summarize(grid: pd.DataFrame) -> pd.DataFrame:
    """Resumen consolidado por empleado."""
    if grid.empty:
        return pd.DataFrame()

    out = []
    for (emp_id, nombre), g in grid.groupby(["employee_id", "empleado"], sort=True):
        laborales = g[g["laboral"] & (g["estado"] != "future")]
        trabajados = g[g["neto_min"] > 0]
        out.append({
            "employee_id": emp_id,
            "Empleado": nombre,
            "Cargo": g["cargo"].iloc[0],
            "Días laborales": int(len(laborales)),
            "Días trabajados": int(len(trabajados)),
            "Horas esperadas": round(laborales["esperado_min"].sum() / 60, 2),
            "Horas trabajadas": round(g["neto_min"].sum() / 60, 2),
            "Horas acreditadas": round(g["acreditado_min"].sum() / 60, 2),
            "Diferencia": round(
                (g["acreditado_min"].sum() - laborales["esperado_min"].sum()) / 60, 2
            ),
            "Tardanzas": int((g["estado"].isin(["late", "late_and_early"])).sum()),
            "Minutos de retraso": int(g["tarde_min"].sum()),
            "Salidas tempranas": int((g["estado"].isin(["early_leave", "late_and_early"])).sum()),
            "Ausencias": int((g["estado"] == "absent").sum()),
            "Justificados": int((g["estado"] == "exception").sum()),
            "Jornadas abiertas": int((g["estado"] == "open").sum()),
            "Horas extra": round(g["extra_min"].sum() / 60, 2),
            "Por revisar": int(g["revisar"].sum()),
        })
    return pd.DataFrame(out)


def incidents(grid: pd.DataFrame) -> pd.DataFrame:
    """Solo los días con algún problema."""
    if grid.empty:
        return pd.DataFrame()
    mask = (
        grid["estado"].isin(["late", "early_leave", "late_and_early", "absent", "open"])
        | grid["revisar"]
        | (grid["estado"] == "exception")
    )
    return grid[mask].copy()


def upcoming_birthdays(employees: list[dict[str, Any]], reference: date | None = None,
                       horizon_days: int = 60) -> list[dict[str, Any]]:
    """Cumpleaños ordenados por cercanía a partir de la fecha de referencia."""
    reference = reference or today_gt()
    result = []
    for emp in employees:
        bd = parse_date(emp.get("birth_date"))
        if bd is None:
            continue
        try:
            next_bd = bd.replace(year=reference.year)
        except ValueError:  # 29 de febrero
            next_bd = date(reference.year, 3, 1)
        if next_bd < reference:
            try:
                next_bd = bd.replace(year=reference.year + 1)
            except ValueError:
                next_bd = date(reference.year + 1, 3, 1)
        delta = (next_bd - reference).days
        if delta > horizon_days:
            continue
        result.append({
            "employee_id": emp["id"],
            "nombre": emp.get("full_name", ""),
            "cargo": emp.get("position") or "",
            "fecha": bd,
            "proximo": next_bd,
            "faltan": delta,
            "edad": next_bd.year - bd.year,
        })
    return sorted(result, key=lambda r: r["faltan"])


def all_birthdays_by_month(employees: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for emp in employees:
        bd = parse_date(emp.get("birth_date"))
        if bd is None:
            continue
        rows.append({
            "Empleado": emp.get("full_name", ""),
            "Cargo": emp.get("position") or "",
            "Mes": bd.month,
            "Día": bd.day,
            "Fecha": bd,
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values(["Mes", "Día"]).reset_index(drop=True)
    return df


def today_status(employees: list[dict[str, Any]], attendance: list[dict[str, Any]],
                 exceptions: list[dict[str, Any]], holidays: list[dict[str, Any]],
                 day: date | None = None) -> pd.DataFrame:
    """Estado en vivo del día para el panel de la gerencia."""
    day = day or today_gt()
    grid = build_grid(employees, attendance, exceptions, holidays, day, day)
    return grid


def scheduled_bounds(employee: dict[str, Any], day: date):
    """Devuelve (entrada_programada, salida_programada) como datetimes locales."""
    start = parse_time(employee.get("shift_start"))
    end = parse_time(employee.get("shift_end"))
    if start is None or end is None:
        return None, None
    dt_in = combine_gt(day, start)
    dt_out = combine_gt(day, end)
    if end <= start:
        dt_out += timedelta(days=1)
    return dt_in, dt_out
