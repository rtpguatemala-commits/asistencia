"""
Modo demostración: corre la aplicación completa con datos ficticios,
sin conexión a Supabase y sin tocar la información real.

Sirve para capacitar al equipo, probar cambios o grabar un video sin
riesgo de ensuciar la base de producción.

Cómo usarlo:

    streamlit run scripts/demo_app.py

Se entra sin contraseña. Para ver la vista de un colaborador normal,
agrega ?role=employee al final de la dirección.
"""

from __future__ import annotations

import datetime as dt
import sys
import uuid
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import streamlit as st  # noqa: E402

from app import db  # noqa: E402
from app.tz import GT, now_gt, today_gt  # noqa: E402

HOY = today_gt()


def _dias_atras(n: int) -> str:
    return str(HOY - dt.timedelta(days=n))


def _iso(dia: str, hora: str) -> str:
    h, m = hora.split(":")
    base = dt.datetime.fromisoformat(dia).replace(hour=int(h), minute=int(m), tzinfo=GT)
    return base.astimezone(dt.timezone.utc).isoformat()


# ---------------------------------------------------------------------
# Datos de demostración
# ---------------------------------------------------------------------
def _empleado(eid, nombre, correo, cargo, rol, nacimiento, entrada, salida):
    return dict(id=eid, full_name=nombre, email=correo, position=cargo, role=rol,
                birth_date=nacimiento, phone=None, shift_start=entrada + ":00",
                shift_end=salida + ":00", work_days=[1, 2, 3, 4, 5],
                lunch_threshold_hours=6, lunch_deduction_minutes=60, grace_minutes=15,
                is_active=True, created_at=_iso(_dias_atras(60), "08:00"))


EMPLOYEES = [
    _empleado("k1", "Licda. Keren Orozco", "keren@ejemplo.org",
              "Gerente de Recursos Humanos", "admin", "1991-12-28", "07:00", "16:00"),
    _empleado("e1", "Edgar Dávila", "edgar@ejemplo.org",
              "Coordinador de campo", "employee", "1990-03-14", "09:00", "18:00"),
    _empleado("e2", "Eddie Bustamante", "eddie@ejemplo.org",
              "Enlace comunitario", "employee", "1994-09-05", "07:30", "16:30"),
    _empleado("e3", "Ellie Gonzáles", "ellie@ejemplo.org",
              "Comunicación y donantes", "employee", "1996-08-01", "10:00", "19:00"),
    _empleado("e4", "José Izquierdo", "jose@ejemplo.org",
              "Asistente administrativo", "employee", "1999-11-22", "10:00", "15:00"),
]

SETTINGS = dict(id=1, org_name="Rescue The Planet Guatemala",
                building_lat=14.606243, building_lng=-90.466834,
                building_radius_m=50, max_gps_accuracy_m=120,
                default_grace_minutes=15, auto_close_enabled=True,
                timezone="America/Guatemala",
                require_work_summary=True, work_summary_min_chars=20)


def _registro(eid, dia, entrada, salida, estado, neto, tarde=0, temprano=0,
              bitacora=None, modo="building", revisar=False):
    return dict(
        id=str(uuid.uuid4()), employee_id=eid, work_date=dia,
        clock_in_at=_iso(dia, entrada),
        clock_out_at=_iso(dia, salida) if salida else None,
        clock_in_mode=modo, clock_out_mode=modo if salida else None,
        clock_in_lat=14.60625, clock_in_lng=-90.46681,
        clock_in_accuracy_m=11, clock_in_distance_m=14.2,
        clock_out_lat=14.60625, clock_out_lng=-90.46681,
        clock_out_accuracy_m=13, clock_out_distance_m=16.8,
        clock_in_reason=None, clock_out_reason=None,
        auto_closed=False, needs_review=revisar,
        gross_minutes=(neto + 60) if salida else None,
        lunch_minutes=60 if salida else None,
        net_minutes=neto if salida else None,
        late_minutes=tarde, early_leave_minutes=temprano, overtime_minutes=0,
        status=estado, note=None, work_summary=bitacora,
        edited_by=None, edited_at=None, created_at=_iso(dia, entrada),
    )


def _habiles(n: int) -> list[str]:
    """Los últimos n días hábiles antes de hoy, del más antiguo al más reciente."""
    dias, d = [], HOY - dt.timedelta(days=1)
    while len(dias) < n:
        if d.isoweekday() <= 5:
            dias.append(str(d))
        d -= dt.timedelta(days=1)
    return list(reversed(dias))


DIAS = _habiles(5)

BITACORAS = {
    "e1": [
        "Supervisé la jornada de reforestación en Villa Nueva con 38 voluntarios y "
        "coordiné el transporte de regreso.",
        "Recorrido de campo en las tres parcelas del vivero y levantamiento fotográfico "
        "para el informe trimestral.",
        "Reunión con la municipalidad por el permiso del vivero y seguimiento a los "
        "proyectos abiertos.",
        "Capacitación a doce promotores comunitarios sobre manejo de residuos.",
        "Cierre del reporte mensual de campo y entrega de insumos a las brigadas.",
    ],
    "e2": [
        "Visité dos escuelas del programa de reciclaje y entregué el material didáctico.",
        "Actualicé el padrón de beneficiarios y di seguimiento a ocho familias del programa.",
        "Coordiné con los líderes comunitarios la jornada de limpieza del río.",
        "Levantamiento de encuestas de impacto en la colonia El Milagro.",
        "Trabajo de campo en la mañana y elaboración del informe de visitas.",
    ],
    "e3": [
        "Publiqué la campaña de donaciones del mes y respondí 24 mensajes de donantes.",
        "Preparé el boletín mensual y edité el material fotográfico de la jornada.",
        "Reunión con dos empresas interesadas en patrocinar el programa educativo.",
        "Actualicé la página web con los resultados del trimestre.",
        "Diseñé las piezas gráficas para la campaña de septiembre.",
    ],
    "e4": [
        "Archivo de expedientes y conciliación de facturas del mes.",
        "Apoyo en la preparación de la reunión de junta y control de caja chica.",
        "Registro de donaciones en el sistema contable y cotizaciones de insumos.",
        "Atención a proveedores y seguimiento a las órdenes de compra pendientes.",
        "Ordené el archivo físico y actualicé el inventario de bodega.",
    ],
    "k1": [
        "Revisión de planillas, entrevistas para la plaza de campo y seguimiento al "
        "plan de capacitación.",
        "Elaboración del reporte de asistencia del mes y reunión con dirección.",
        "Inducción a personal nuevo y actualización de los expedientes laborales.",
        "Revisión de contratos y coordinación de la evaluación de desempeño.",
        "Planificación del cronograma de vacaciones del equipo.",
    ],
}

HORARIOS = {
    "k1": ("07:00", "16:00"), "e1": ("09:00", "18:00"), "e2": ("07:30", "16:30"),
    "e3": ("10:00", "19:00"), "e4": ("10:00", "15:00"),
}


def _normal(eid, dia, indice):
    entrada, salida = HORARIOS[eid]
    h, m = entrada.split(":")
    entrada_real = f"{h}:{int(m) + 2 + (indice % 4):02d}"
    hs, ms = salida.split(":")
    salida_real = f"{hs}:{int(ms) + 1:02d}" if int(ms) < 58 else salida
    bruto = _minutos_horario(entrada_real, salida_real)
    almuerzo = 60 if bruto > 360 else 0
    return _registro(eid, dia, entrada_real, salida_real, "on_time", bruto - almuerzo,
                     bitacora=BITACORAS[eid][indice % len(BITACORAS[eid])])


def _minutos_horario(a, b):
    ha, ma = (int(x) for x in a.split(":"))
    hb, mb = (int(x) for x in b.split(":"))
    return (hb * 60 + mb) - (ha * 60 + ma)


ATTENDANCE = []
for _i, _dia in enumerate(DIAS):
    for _eid in ("k1", "e1", "e2", "e3", "e4"):
        ATTENDANCE.append(_normal(_eid, _dia, _i))

# --- Incidencias sembradas para la demostración ---
def _reemplazar(eid, dia, registro):
    global ATTENDANCE
    ATTENDANCE = [r for r in ATTENDANCE if not (r["employee_id"] == eid and r["work_date"] == dia)]
    if registro is not None:
        ATTENDANCE.append(registro)


# Eddie salió temprano el último día hábil (cita médica)
_reemplazar("e2", DIAS[-1], _registro(
    "e2", DIAS[-1], "07:32", "14:05", "early_leave", 333, temprano=145,
    bitacora="Trabajo de campo en la mañana en la colonia El Milagro. Me retiré antes "
             "de la hora por una cita médica."))

# Edgar llegó tarde hace dos días hábiles
_reemplazar("e1", DIAS[-2], _registro(
    "e1", DIAS[-2], "09:48", "18:00", "late", 432, tarde=48,
    bitacora="Reunión con la municipalidad por el permiso del vivero y seguimiento a "
             "los tres proyectos abiertos del trimestre."))

# José no marcó hace tres días hábiles
_reemplazar("e4", DIAS[-3], None)

# Jornadas abiertas de hoy: quien use la demo puede cerrarlas
ATTENDANCE.append(_registro("k1", str(HOY), "07:02", None, "open", 0))
ATTENDANCE.append(_registro("e1", str(HOY), "09:06", None, "open", 0))

EXCEPTIONS = [
    dict(id=str(uuid.uuid4()), employee_id="e3", date_from=DIAS[-1],
         date_to=DIAS[-1], type="field_work",
         note="Cobertura del evento de siembra en Amatitlán.",
         attachment_url=None, counts_as_paid=True, created_by="k1",
         created_at=_iso(_dias_atras(2), "08:00")),
]

HOLIDAYS = [
    dict(id=str(uuid.uuid4()), date="2026-09-15", name="Día de la Independencia",
         is_half_day=False, created_at=_iso(_dias_atras(30), "08:00")),
    dict(id=str(uuid.uuid4()), date="2026-10-20", name="Día de la Revolución",
         is_half_day=False, created_at=_iso(_dias_atras(30), "08:00")),
]

CORRECTIONS = [
    dict(id=str(uuid.uuid4()), attendance_id=None, employee_id="e4",
         work_date=DIAS[-3], requested_clock_in=_iso(DIAS[-3], "10:00"),
         requested_clock_out=_iso(DIAS[-3], "15:00"),
         reason="Olvidé marcar la salida porque salí directo a dejar unos documentos.",
         status="pending", reviewed_by=None, reviewed_at=None, review_note=None,
         created_at=_iso(_dias_atras(3), "09:00")),
]

AUDIT = [
    dict(id=1, actor_id="k1", actor_name="Licda. Keren Orozco", action="update_settings",
         entity="settings", entity_id="1", details={"radius": 50},
         created_at=_iso(_dias_atras(5), "09:12")),
]

# Streamlit vuelve a ejecutar este archivo en cada interacción, así que los datos
# se guardan en la sesión: de lo contrario cada clic reiniciaría la demostración.
if "_demo_datos" not in st.session_state:
    st.session_state["_demo_datos"] = {
        "employees": EMPLOYEES,
        "settings": [SETTINGS],
        "attendance": ATTENDANCE,
        "exceptions": EXCEPTIONS,
        "holidays": HOLIDAYS,
        "correction_requests": CORRECTIONS,
        "audit_log": AUDIT,
    }

TABLES = st.session_state["_demo_datos"]
EMPLOYEES = TABLES["employees"]
SETTINGS = TABLES["settings"][0]
ATTENDANCE = TABLES["attendance"]
EXCEPTIONS = TABLES["exceptions"]
HOLIDAYS = TABLES["holidays"]
CORRECTIONS = TABLES["correction_requests"]
AUDIT = TABLES["audit_log"]


# ---------------------------------------------------------------------
# Cliente falso de Supabase, con filtros y escrituras en memoria
# ---------------------------------------------------------------------
class _Res:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, tabla: str):
        self.tabla = tabla
        self.filtros: list[tuple] = []
        self.accion = "select"
        self.payload = None
        self._negar = False

    # --- filtros ---
    def _add(self, op, col, val):
        self.filtros.append((op, col, val, self._negar))
        self._negar = False
        return self

    def eq(self, c, v):  return self._add("eq", c, v)
    def gte(self, c, v): return self._add("gte", c, v)
    def lte(self, c, v): return self._add("lte", c, v)
    def lt(self, c, v):  return self._add("lt", c, v)
    def gt(self, c, v):  return self._add("gt", c, v)
    def is_(self, c, v): return self._add("is", c, v)

    @property
    def not_(self):
        self._negar = True
        return self

    def select(self, *a, **k): return self
    def order(self, *a, **k):  return self
    def limit(self, *a, **k):  return self

    # --- escrituras ---
    def insert(self, payload, **k):
        self.accion, self.payload = "insert", payload
        return self

    def update(self, payload, **k):
        self.accion, self.payload = "update", payload
        return self

    def upsert(self, payload, **k):
        self.accion, self.payload = "upsert", payload
        return self

    def delete(self, **k):
        self.accion = "delete"
        return self

    # --- ejecución ---
    def _coincide(self, fila) -> bool:
        for op, col, val, negar in self.filtros:
            actual = fila.get(col)
            if op == "eq":
                ok = str(actual) == str(val)
            elif op == "is":
                ok = actual is None if str(val).lower() == "null" else actual == val
            elif op in ("gte", "lte", "lt", "gt"):
                if actual is None:
                    ok = False
                else:
                    a, b = str(actual)[:10], str(val)[:10]
                    ok = {"gte": a >= b, "lte": a <= b, "lt": a < b, "gt": a > b}[op]
            else:
                ok = True
            if negar:
                ok = not ok
            if not ok:
                return False
        return True

    def execute(self):
        filas = TABLES.setdefault(self.tabla, [])
        if self.accion == "select":
            return _Res([f for f in filas if self._coincide(f)])
        if self.accion in ("insert", "upsert"):
            nuevas = self.payload if isinstance(self.payload, list) else [self.payload]
            creadas = []
            for n in nuevas:
                n = dict(n)
                n.setdefault("id", str(uuid.uuid4()))
                n.setdefault("created_at", now_gt().isoformat())
                filas.append(n)
                creadas.append(n)
            return _Res(creadas)
        if self.accion == "update":
            tocadas = []
            for f in filas:
                if self._coincide(f):
                    f.update(self.payload)
                    tocadas.append(f)
            return _Res(tocadas)
        if self.accion == "delete":
            quedan = [f for f in filas if not self._coincide(f)]
            borradas = [f for f in filas if self._coincide(f)]
            TABLES[self.tabla] = quedan
            return _Res(borradas)
        return _Res([])


def _minutos(desde_iso: str, hasta) -> int:
    a = dt.datetime.fromisoformat(str(desde_iso).replace("Z", "+00:00"))
    b = hasta if isinstance(hasta, dt.datetime) else dt.datetime.fromisoformat(str(hasta))
    return int((b - a).total_seconds() // 60)


class _Rpc:
    def __init__(self, nombre, payload):
        self.nombre, self.payload = nombre, payload or {}

    def execute(self):
        uid = st.session_state.get("user_id")
        if self.nombre == "clock_out":
            resumen = (self.payload.get("p_summary") or "").strip()
            minimo = int(SETTINGS["work_summary_min_chars"])
            if SETTINGS["require_work_summary"] and len(resumen) < minimo:
                raise RuntimeError(
                    f"Antes de cerrar tu jornada describe las tareas que realizaste hoy "
                    f"(mínimo {minimo} caracteres)."
                )
            abiertos = [a for a in ATTENDANCE
                        if a["employee_id"] == uid and a["clock_out_at"] is None]
            if not abiertos:
                raise RuntimeError("No tienes una jornada abierta. Primero marca tu entrada.")
            r = abiertos[-1]
            ahora = now_gt()
            r["clock_out_at"] = ahora.astimezone(dt.timezone.utc).isoformat()
            r["clock_out_mode"] = self.payload.get("p_mode")
            r["clock_out_reason"] = self.payload.get("p_reason")
            r["work_summary"] = resumen
            bruto = max(0, _minutos(r["clock_in_at"], ahora))
            almuerzo = 60 if bruto > 360 else 0
            r["gross_minutes"], r["lunch_minutes"] = bruto, min(almuerzo, bruto)
            r["net_minutes"] = bruto - min(almuerzo, bruto)
            r["status"] = "on_time" if r["late_minutes"] <= 15 else "late"
            return _Res([r])

        if self.nombre == "clock_in":
            ahora = now_gt()
            nuevo = _registro(uid, str(HOY), ahora.strftime("%H:%M"), None, "open", 0,
                              modo=self.payload.get("p_mode", "building"))
            ATTENDANCE.append(nuevo)
            return _Res([nuevo])

        if self.nombre == "justify_day":
            nueva = dict(
                id=str(uuid.uuid4()),
                employee_id=self.payload["p_employee_id"],
                date_from=str(self.payload["p_date"]),
                date_to=str(self.payload["p_date"]),
                type=self.payload["p_type"],
                note=self.payload.get("p_note"),
                attachment_url=None,
                counts_as_paid=bool(self.payload.get("p_paid", True)),
                created_by=uid,
                created_at=now_gt().isoformat(),
            )
            EXCEPTIONS.append(nueva)
            for a in ATTENDANCE:
                if (a["employee_id"] == nueva["employee_id"]
                        and a["work_date"] == nueva["date_from"]):
                    a["needs_review"] = False
            return _Res([nueva])

        if self.nombre == "approve_correction":
            for c in CORRECTIONS:
                if c["id"] == self.payload.get("p_request_id"):
                    c["status"] = "approved"
            return _Res([])

        return _Res([])


class _Cliente:
    def table(self, nombre): return _Query(nombre)
    def rpc(self, nombre, payload=None): return _Rpc(nombre, payload)


# ---------------------------------------------------------------------
# Sustitución de la capa de datos
# ---------------------------------------------------------------------
db.client = lambda: _Cliente()
db.admin_client = lambda: None
db.secrets_ok = lambda: True
db.fetch_employees = lambda include_inactive=False: list(EMPLOYEES)
db.fetch_settings = lambda: SETTINGS
db.fetch_attendance = lambda a, b, employee_id=None: [
    r for r in ATTENDANCE
    if str(a) <= r["work_date"] <= str(b) and (not employee_id or r["employee_id"] == employee_id)
]
db.fetch_exceptions = lambda a=None, b=None, employee_id=None: [
    x for x in EXCEPTIONS
    if (a is None or x["date_to"] >= str(a)) and (b is None or x["date_from"] <= str(b))
    and (not employee_id or x["employee_id"] == employee_id)
]
db.fetch_holidays = lambda a=None, b=None: [
    h for h in HOLIDAYS
    if (a is None or h["date"] >= str(a)) and (b is None or h["date"] <= str(b))
]
db.fetch_correction_requests = lambda status=None: [
    c for c in CORRECTIONS if status is None or c["status"] == status
]
db.log_action = lambda *a, **k: None


# ---------------------------------------------------------------------
# Sesión simulada y arranque de la aplicación real
# ---------------------------------------------------------------------
ROL = st.query_params.get("role", "admin")
PERFIL = EMPLOYEES[0] if ROL == "admin" else EMPLOYEES[1]
st.session_state.user_id = PERFIL["id"]
st.session_state.profile = PERFIL

import streamlit_app  # noqa: E402

streamlit_app.main()
