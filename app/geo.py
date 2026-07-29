"""Geolocalización del navegador y cálculo de distancia al edificio."""

from __future__ import annotations

import math
from typing import Any

import streamlit as st

try:
    from streamlit_js_eval import get_geolocation
    JS_EVAL_OK = True
except Exception:  # pragma: no cover
    JS_EVAL_OK = False

    def get_geolocation(component_key: str | None = None):  # type: ignore
        return None


EARTH_RADIUS_M = 6371000.0


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Distancia en metros entre dos coordenadas."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def read_location(key: str) -> dict[str, Any] | None:
    """Pide la ubicación al navegador.

    Devuelve {'lat', 'lng', 'accuracy'} o None si aún no responde
    o si el usuario denegó el permiso.
    """
    if not JS_EVAL_OK:
        return None
    try:
        raw = get_geolocation(component_key=key)
    except TypeError:
        raw = get_geolocation()
    except Exception:
        return None

    if not raw:
        return None
    coords = raw.get("coords") if isinstance(raw, dict) else None
    if not coords:
        return None
    lat, lng = coords.get("latitude"), coords.get("longitude")
    if lat is None or lng is None:
        return None
    return {
        "lat": float(lat),
        "lng": float(lng),
        "accuracy": float(coords.get("accuracy") or 0.0),
    }


def evaluate(location: dict[str, Any] | None, settings: dict[str, Any]) -> dict[str, Any]:
    """Compara la ubicación contra la geocerca configurada.

    Devuelve un resumen listo para pintar en pantalla. La validación real
    y definitiva la hace Postgres dentro de clock_in / clock_out.
    """
    radius = float(settings.get("building_radius_m") or 50)
    max_acc = float(settings.get("max_gps_accuracy_m") or 120)
    b_lat = float(settings.get("building_lat") or 14.606243)
    b_lng = float(settings.get("building_lng") or -90.466834)

    if not location:
        return {
            "ok": False,
            "distance": None,
            "accuracy": None,
            "radius": radius,
            "reason": "sin_ubicacion",
            "message": "Esperando la ubicación del dispositivo…",
        }

    distance = haversine_m(location["lat"], location["lng"], b_lat, b_lng)
    accuracy = location.get("accuracy") or 0.0

    if accuracy and accuracy > max_acc:
        return {
            "ok": False,
            "distance": distance,
            "accuracy": accuracy,
            "radius": radius,
            "reason": "precision_baja",
            "message": (f"La señal de GPS es imprecisa (± {accuracy:.0f} m). "
                        "Acércate a una ventana o sal al aire libre."),
        }

    if distance > radius:
        return {
            "ok": False,
            "distance": distance,
            "accuracy": accuracy,
            "radius": radius,
            "reason": "fuera_de_rango",
            "message": (f"Estás a {distance:.0f} m del edificio. "
                        f"El máximo permitido es {radius:.0f} m."),
        }

    return {
        "ok": True,
        "distance": distance,
        "accuracy": accuracy,
        "radius": radius,
        "reason": "dentro",
        "message": f"Dentro del edificio · a {distance:.0f} m del punto central.",
    }


def cached_location(key: str) -> dict[str, Any] | None:
    """Guarda la última lectura válida en la sesión para evitar parpadeos."""
    reading = read_location(key)
    if reading:
        st.session_state["geo"] = reading
        return reading
    return st.session_state.get("geo")
