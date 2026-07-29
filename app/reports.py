"""Generación del reporte de horas trabajadas en Excel."""

from __future__ import annotations

from datetime import date
from io import BytesIO

import pandas as pd
import xlsxwriter

from .analytics import incidents, summarize
from .config import ORG_NAME
from .tz import fmt_date, hhmm, is_missing, now_gt

# Paleta del reporte
INK = "#101114"
GOLD = "#E8B84B"
GREEN = "#2F7D5B"
AMBER = "#B77A17"
RED = "#A83A32"
GREY = "#6B6C74"

DETAIL_COLUMNS = [
    ("Empleado",          "empleado",         22),
    ("Cargo",             "cargo",            20),
    ("Fecha",             "fecha",            12),
    ("Día",               "dia",              11),
    ("Horario",           "horario",          14),
    ("Entrada",           "_entrada",          9),
    ("Salida",            "_salida",           9),
    ("Modo entrada",      "_modo_entrada",    13),
    ("Modo salida",       "_modo_salida",     13),
    ("Distancia (m)",     "distancia_m",      12),
    ("Motivo ubicación",  "motivo_ubicacion", 26),
    ("Bruto (h)",         "_bruto_h",         10),
    ("Almuerzo (min)",    "almuerzo_min",     13),
    ("Netas (h)",         "_neto_h",          10),
    ("Esperadas (h)",     "_esperado_h",      12),
    ("Retraso (min)",     "tarde_min",        12),
    ("Salida temprana",   "temprano_min",     14),
    ("Extra (min)",       "extra_min",        11),
    ("Estado",            "estado_texto",     18),
    ("Asueto",            "asueto",           24),
    ("Excepción",         "excepcion",        20),
    ("Observación",       "observacion",      30),
]

MODE_LABELS = {"building": "Edificio", "other": "Otro lugar", "": "—"}


def _prepare_detail(grid: pd.DataFrame) -> pd.DataFrame:
    df = grid.copy()
    df["_entrada"] = df["entrada"].apply(lambda d: hhmm(d, ""))
    df["_salida"] = df["salida"].apply(lambda d: hhmm(d, ""))
    df["_modo_entrada"] = df["modo_entrada"].map(lambda m: MODE_LABELS.get(m or "", "—"))
    df["_modo_salida"] = df["modo_salida"].map(lambda m: MODE_LABELS.get(m or "", "—"))
    df["_bruto_h"] = (df["bruto_min"] / 60).round(2)
    df["_neto_h"] = (df["neto_min"] / 60).round(2)
    df["_esperado_h"] = (df["esperado_min"] / 60).round(2)
    df["distancia_m"] = df["distancia_m"].apply(
        lambda v: round(float(v), 1) if not is_missing(v) else ""
    )
    return df


def _write_table(wb, ws, df: pd.DataFrame, columns, formats, start_row: int = 3) -> int:
    header_fmt = formats["header"]
    ws.set_row(start_row, 26)
    for col_idx, (title, _key, width) in enumerate(columns):
        ws.write(start_row, col_idx, title, header_fmt)
        ws.set_column(col_idx, col_idx, width)

    row = start_row + 1
    for _, record in df.iterrows():
        estado = record.get("estado", "")
        base = formats["cell"]
        if estado == "absent":
            base = formats["cell_red"]
        elif estado in ("late", "early_leave", "late_and_early"):
            base = formats["cell_amber"]
        elif estado == "on_time":
            base = formats["cell_green"]
        elif estado in ("rest", "holiday", "future"):
            base = formats["cell_grey"]

        for col_idx, (_title, key, _w) in enumerate(columns):
            value = record.get(key, "")
            if isinstance(value, date):
                ws.write_datetime(row, col_idx, value, formats["date"])
            elif value is None or (isinstance(value, float) and pd.isna(value)):
                ws.write_blank(row, col_idx, None, base)
            elif isinstance(value, bool):
                ws.write(row, col_idx, "Sí" if value else "No", base)
            else:
                ws.write(row, col_idx, value, base)
        row += 1

    if len(df) > 0:
        ws.autofilter(start_row, 0, row - 1, len(columns) - 1)
        ws.freeze_panes(start_row + 1, 3)
    return row


def _title_block(ws, formats, titulo: str, subtitulo: str) -> None:
    ws.write(0, 0, ORG_NAME, formats["title"])
    ws.write(1, 0, titulo, formats["subtitle"])
    ws.write(2, 0, subtitulo, formats["muted"])


def build_report(
    grid: pd.DataFrame,
    date_from: date,
    date_to: date,
    generated_by: str = "",
) -> bytes:
    """Devuelve el archivo .xlsx como bytes."""
    output = BytesIO()
    wb = xlsxwriter.Workbook(output, {"in_memory": True, "default_date_format": "dd/mm/yyyy"})

    f = {
        "title":    wb.add_format({"bold": True, "font_size": 15, "font_color": INK}),
        "subtitle": wb.add_format({"bold": True, "font_size": 11, "font_color": GOLD}),
        "muted":    wb.add_format({"font_size": 9, "font_color": GREY, "italic": True}),
        "header":   wb.add_format({
            "bold": True, "font_size": 9, "font_color": "#FFFFFF", "bg_color": INK,
            "align": "center", "valign": "vcenter", "text_wrap": True, "border": 1,
            "border_color": "#333438",
        }),
        "cell":       wb.add_format({"font_size": 10, "border": 1, "border_color": "#DDDDE1"}),
        "cell_green": wb.add_format({"font_size": 10, "border": 1, "border_color": "#DDDDE1",
                                     "bg_color": "#EAF6F0", "font_color": GREEN}),
        "cell_amber": wb.add_format({"font_size": 10, "border": 1, "border_color": "#DDDDE1",
                                     "bg_color": "#FDF3E2", "font_color": AMBER}),
        "cell_red":   wb.add_format({"font_size": 10, "border": 1, "border_color": "#DDDDE1",
                                     "bg_color": "#FCEDEC", "font_color": RED}),
        "cell_grey":  wb.add_format({"font_size": 10, "border": 1, "border_color": "#DDDDE1",
                                     "font_color": GREY}),
        "date":       wb.add_format({"font_size": 10, "border": 1, "border_color": "#DDDDE1",
                                     "num_format": "dd/mm/yyyy"}),
        "num":        wb.add_format({"font_size": 10, "border": 1, "border_color": "#DDDDE1",
                                     "num_format": "0.00"}),
        "int":        wb.add_format({"font_size": 10, "border": 1, "border_color": "#DDDDE1",
                                     "num_format": "0"}),
        "bold":       wb.add_format({"bold": True, "font_size": 10, "border": 1,
                                     "border_color": "#DDDDE1"}),
    }

    periodo = f"Período: {fmt_date(date_from)} al {fmt_date(date_to)}"
    pie = f"Generado el {fmt_date(now_gt().date())} a las {now_gt().strftime('%H:%M')} (hora de Guatemala)"
    if generated_by:
        pie += f" por {generated_by}"

    # ---------------- Hoja 1: Detalle diario ----------------
    ws1 = wb.add_worksheet("Detalle diario")
    ws1.hide_gridlines(2)
    _title_block(ws1, f, "Detalle diario de asistencia", f"{periodo} · {pie}")
    detalle = _prepare_detail(grid)
    _write_table(wb, ws1, detalle, DETAIL_COLUMNS, f)

    # ---------------- Hoja 2: Resumen ----------------
    resumen = summarize(grid)
    ws2 = wb.add_worksheet("Resumen")
    ws2.hide_gridlines(2)
    _title_block(ws2, f, "Resumen consolidado por empleado", f"{periodo} · {pie}")

    if not resumen.empty:
        cols = [c for c in resumen.columns if c != "employee_id"]
        ws2.set_row(3, 26)
        for i, title in enumerate(cols):
            ws2.write(3, i, title, f["header"])
            ws2.set_column(i, i, max(12, min(26, len(title) + 6)))
        for r, (_, rec) in enumerate(resumen.iterrows(), start=4):
            for i, title in enumerate(cols):
                value = rec[title]
                if isinstance(value, float):
                    ws2.write_number(r, i, float(value), f["num"])
                elif isinstance(value, (int,)) and not isinstance(value, bool):
                    ws2.write_number(r, i, int(value), f["int"])
                else:
                    ws2.write(r, i, value, f["cell"])
        last = 3 + len(resumen)
        ws2.autofilter(3, 0, last, len(cols) - 1)
        ws2.freeze_panes(4, 1)

        # Resaltar diferencias negativas
        if "Diferencia" in cols:
            idx = cols.index("Diferencia")
            ws2.conditional_format(4, idx, last, idx, {
                "type": "cell", "criteria": "<", "value": 0,
                "format": wb.add_format({"font_color": RED, "bold": True,
                                         "border": 1, "border_color": "#DDDDE1",
                                         "num_format": "0.00"}),
            })
    else:
        ws2.write(4, 0, "No hay datos en el período seleccionado.", f["muted"])

    # ---------------- Hoja 3: Incidencias ----------------
    ws3 = wb.add_worksheet("Incidencias")
    ws3.hide_gridlines(2)
    _title_block(ws3, f, "Días con incidencia",
                 "Tardanzas, salidas tempranas, ausencias, jornadas sin cerrar y justificaciones")
    inc = incidents(grid)
    if not inc.empty:
        _write_table(wb, ws3, _prepare_detail(inc), DETAIL_COLUMNS, f)
    else:
        ws3.write(4, 0, "Sin incidencias en el período. ¡Excelente!", f["muted"])

    # ---------------- Hoja 4: Gráficas ----------------
    ws4 = wb.add_worksheet("Gráficas")
    ws4.hide_gridlines(2)
    _title_block(ws4, f, "Gráficas del período", periodo)

    if not resumen.empty:
        # Tabla auxiliar para alimentar las gráficas
        ws4.write(4, 0, "Empleado", f["header"])
        ws4.write(4, 1, "Horas trabajadas", f["header"])
        ws4.write(4, 2, "Horas esperadas", f["header"])
        ws4.write(4, 3, "Tardanzas", f["header"])
        ws4.write(4, 4, "Ausencias", f["header"])
        ws4.set_column(0, 0, 24)
        ws4.set_column(1, 4, 16)

        for i, (_, rec) in enumerate(resumen.iterrows(), start=5):
            ws4.write(i, 0, rec["Empleado"], f["cell"])
            ws4.write_number(i, 1, float(rec["Horas trabajadas"]), f["num"])
            ws4.write_number(i, 2, float(rec["Horas esperadas"]), f["num"])
            ws4.write_number(i, 3, int(rec["Tardanzas"]), f["int"])
            ws4.write_number(i, 4, int(rec["Ausencias"]), f["int"])

        n = len(resumen)
        first, last = 5, 4 + n

        chart1 = wb.add_chart({"type": "column"})
        chart1.add_series({
            "name": "Horas trabajadas",
            "categories": ["Gráficas", first, 0, last, 0],
            "values":     ["Gráficas", first, 1, last, 1],
            "fill": {"color": GOLD},
        })
        chart1.add_series({
            "name": "Horas esperadas",
            "categories": ["Gráficas", first, 0, last, 0],
            "values":     ["Gráficas", first, 2, last, 2],
            "fill": {"color": "#8E8F97"},
        })
        chart1.set_title({"name": "Horas trabajadas vs. esperadas"})
        chart1.set_y_axis({"name": "Horas"})
        chart1.set_size({"width": 640, "height": 340})
        chart1.set_legend({"position": "bottom"})
        ws4.insert_chart(4, 6, chart1)

        chart2 = wb.add_chart({"type": "column"})
        chart2.add_series({
            "name": "Tardanzas",
            "categories": ["Gráficas", first, 0, last, 0],
            "values":     ["Gráficas", first, 3, last, 3],
            "fill": {"color": AMBER},
        })
        chart2.add_series({
            "name": "Ausencias",
            "categories": ["Gráficas", first, 0, last, 0],
            "values":     ["Gráficas", first, 4, last, 4],
            "fill": {"color": RED},
        })
        chart2.set_title({"name": "Tardanzas y ausencias"})
        chart2.set_y_axis({"name": "Días"})
        chart2.set_size({"width": 640, "height": 340})
        chart2.set_legend({"position": "bottom"})
        ws4.insert_chart(23, 6, chart2)
    else:
        ws4.write(4, 0, "No hay datos suficientes para graficar.", f["muted"])

    wb.close()
    output.seek(0)
    return output.getvalue()


def report_filename(date_from: date, date_to: date) -> str:
    return f"Asistencia_RDP_{date_from:%Y%m%d}_{date_to:%Y%m%d}.xlsx"
