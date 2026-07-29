"""Driver de autoprueba: renderiza cada pantalla con datos falsos, sin red."""
import datetime as dt, sys, traceback
import streamlit as st

from app import db, auth

# ---------------- Cliente falso de Supabase ----------------
TODAY = dt.date.today()

EMPLOYEES = [
    dict(id="e1", full_name="Edgar Dávila", email="edgar@x.gt", position="Coordinador",
         role="employee", birth_date="1990-03-14", phone=None, shift_start="09:00:00",
         shift_end="18:00:00", work_days=[1,2,3,4,5], lunch_threshold_hours=6,
         lunch_deduction_minutes=60, grace_minutes=15, is_active=True),
    dict(id="k1", full_name="Keren Orozco", email="keren@x.gt", position="Gerente de RRHH",
         role="admin", birth_date="1991-12-28", phone=None, shift_start="07:00:00",
         shift_end="16:00:00", work_days=[1,2,3,4,5], lunch_threshold_hours=6,
         lunch_deduction_minutes=60, grace_minutes=15, is_active=True),
]
SETTINGS = dict(id=1, org_name="RDP", building_lat=14.606243, building_lng=-90.466834,
                building_radius_m=50, max_gps_accuracy_m=120, default_grace_minutes=15,
                auto_close_enabled=True, timezone="America/Guatemala")
ATT = [dict(id="a1", employee_id="e1", work_date=str(TODAY - dt.timedelta(days=1)),
            clock_in_at=f"{TODAY - dt.timedelta(days=1)}T15:03:00+00:00",
            clock_out_at=f"{TODAY}T00:00:00+00:00", clock_in_mode="building",
            clock_out_mode="building", clock_in_distance_m=18.4, clock_in_reason=None,
            gross_minutes=537, lunch_minutes=60, net_minutes=477, late_minutes=3,
            early_leave_minutes=0, overtime_minutes=0, status="on_time",
            needs_review=False, auto_closed=False, note=None)]
EXC = [dict(id="x1", employee_id="e1", date_from=str(TODAY), date_to=str(TODAY),
            type="vacation", note="Prueba", counts_as_paid=True, attachment_url=None)]
HOL = [dict(id="h1", date=str(TODAY), name="Asueto de prueba", is_half_day=False)]
REQ = [dict(id="r1", attendance_id="a1", employee_id="e1", work_date=str(TODAY),
            requested_clock_in=f"{TODAY}T15:00:00+00:00",
            requested_clock_out=f"{TODAY}T23:00:00+00:00", reason="Olvidé marcar",
            status="pending", reviewed_by=None, reviewed_at=None, review_note=None,
            created_at=f"{TODAY}T18:00:00+00:00")]
AUDIT = [dict(id=1, actor_id="k1", actor_name="Keren Orozco", action="clock_in",
              entity="attendance", entity_id="a1", details={},
              created_at=f"{TODAY}T15:03:00+00:00")]

TABLES = {"employees": EMPLOYEES, "settings": [SETTINGS], "attendance": ATT,
          "exceptions": EXC, "holidays": HOL, "correction_requests": REQ, "audit_log": AUDIT}

class Result:
    def __init__(self, data): self.data = data

class Query:
    def __init__(self, name): self.name = name
    def __getattr__(self, item):
        if item == "not_": return self
        def call(*a, **k): return self
        return call
    def execute(self): return Result(list(TABLES.get(self.name, [])))

class FakeClient:
    def table(self, name): return Query(name)
    def rpc(self, name, payload=None): return Query("_rpc")
    @property
    def auth(self): return self

db.client = lambda: FakeClient()
db.admin_client = lambda: None
db.fetch_employees = lambda include_inactive=False: EMPLOYEES
db.fetch_settings = lambda: SETTINGS
db.fetch_attendance = lambda a, b, employee_id=None: ATT
db.fetch_exceptions = lambda a=None, b=None, employee_id=None: EXC
db.fetch_holidays = lambda a=None, b=None: HOL
db.fetch_correction_requests = lambda status=None: (REQ if status in (None, "pending") else [])
db.log_action = lambda *a, **k: None

# ---------------- Sesión simulada ----------------
ROLE = st.query_params.get("role", "admin")
PERFIL = EMPLOYEES[1] if ROLE == "admin" else EMPLOYEES[0]
st.session_state.user_id = PERFIL["id"]
st.session_state.profile = PERFIL

from app import theme
from app.views import (admin_employees, admin_exceptions, admin_live, admin_records,
                       admin_reports, admin_requests, admin_settings, birthdays,
                       clock, history, profile, stats)

theme.inject_css()

VISTAS = [("clock", clock), ("history", history), ("stats", stats),
          ("birthdays", birthdays), ("profile", profile)]
if ROLE == "admin":
    VISTAS += [("admin_live", admin_live), ("admin_records", admin_records),
               ("admin_employees", admin_employees), ("admin_exceptions", admin_exceptions),
               ("admin_requests", admin_requests), ("admin_reports", admin_reports),
               ("admin_settings", admin_settings)]

errores = []
for nombre, modulo in VISTAS:
    try:
        modulo.render()
        st.text(f"OK::{nombre}")
    except Exception:
        errores.append(nombre)
        st.text(f"FALLA::{nombre}::{traceback.format_exc()}")

st.text("SIN_ERRORES" if not errores else "CON_ERRORES::" + ",".join(errores))
