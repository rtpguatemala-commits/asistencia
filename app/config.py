"""Constantes y paleta de la organización."""

from __future__ import annotations

ORG_NAME = "Rescue The Planet Guatemala"
APP_NAME = "Control de Asistencia"
TIMEZONE = "America/Guatemala"

# Paleta tomada del logo (blanco sobre negro) más acentos funcionales.
COLORS = {
    "bg":        "#0B0B0D",
    "surface":   "#17181C",
    "surface_2": "#212329",
    "border":    "#2E3037",
    "text":      "#F5F5F4",
    "muted":     "#9A9BA3",
    "primary":   "#E8B84B",
    "primary_d": "#C99A2E",
    "success":   "#3FB27F",
    "warning":   "#E9A13B",
    "danger":    "#D2544B",
    "info":      "#5B9BD5",
}

# Etiquetas de estado en español
STATUS_LABELS = {
    "on_time":        "A tiempo",
    "late":           "Tarde",
    "early_leave":    "Salida temprana",
    "late_and_early": "Tarde y salida temprana",
    "open":           "Jornada abierta",
    "absent":         "Ausente",
    "holiday":        "Asueto",
    "exception":      "Justificado",
    "rest":           "Descanso",
    "future":         "Pendiente",
}

STATUS_COLORS = {
    "on_time":        COLORS["success"],
    "late":           COLORS["warning"],
    "early_leave":    COLORS["warning"],
    "late_and_early": COLORS["danger"],
    "open":           COLORS["info"],
    "absent":         COLORS["danger"],
    "holiday":        COLORS["muted"],
    "exception":      COLORS["info"],
    "rest":           COLORS["border"],
    "future":         COLORS["border"],
}

EXCEPTION_LABELS = {
    "vacation":       "Vacaciones",
    "day_off":        "Día libre",
    "sick_leave":     "Incapacidad / médico",
    "personal_leave": "Permiso personal",
    "justified_late": "Tardanza justificada",
}

DAY_NAMES = {
    1: "Lunes", 2: "Martes", 3: "Miércoles", 4: "Jueves",
    5: "Viernes", 6: "Sábado", 7: "Domingo",
}

MONTH_NAMES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
    7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre",
    11: "Noviembre", 12: "Diciembre",
}
