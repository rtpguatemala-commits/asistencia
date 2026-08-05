"""Estilos, encabezados y componentes visuales reutilizables."""

from __future__ import annotations

import base64
from contextlib import contextmanager
from pathlib import Path

import streamlit as st

from .config import APP_NAME, COLORS, ORG_NAME, STATUS_COLORS, STATUS_LABELS

STATIC = Path(__file__).resolve().parent.parent / "static"


def logo_data_uri() -> str:
    path = STATIC / "logo.png"
    if not path.exists():
        return ""
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()


PWA_SNIPPET = """
<script>
(function () {
  try {
    var doc = window.parent.document;
    if (!doc || doc.getElementById("rdp-pwa-manifest")) return;

    function add(tag, attrs, id) {
      var el = doc.createElement(tag);
      el.id = id;
      Object.keys(attrs).forEach(function (k) { el.setAttribute(k, attrs[k]); });
      doc.head.appendChild(el);
    }

    add("link", {rel: "manifest", href: "app/static/manifest.json"}, "rdp-pwa-manifest");
    add("link", {rel: "apple-touch-icon", href: "app/static/icon-180.png"}, "rdp-pwa-touch");
    add("meta", {name: "apple-mobile-web-app-capable", content: "yes"}, "rdp-pwa-capable");
    add("meta", {name: "mobile-web-app-capable", content: "yes"}, "rdp-pwa-capable2");
    add("meta", {name: "apple-mobile-web-app-title", content: "Asistencia RDP"}, "rdp-pwa-title");
    add("meta", {name: "apple-mobile-web-app-status-bar-style",
                 content: "black-translucent"}, "rdp-pwa-bar");
    add("meta", {name: "theme-color", content: "#0B0B0D"}, "rdp-pwa-theme");
  } catch (e) { /* si el navegador lo bloquea, la app sigue funcionando igual */ }
})();
</script>
"""


def pwa_head() -> None:
    """Inyecta el manifiesto y los íconos en el <head> real del documento.

    Streamlit no expone el head, así que se hace desde un componente
    con JavaScript. Si falla, la app funciona igual: solo se pierde la
    instalación con ícono propio.
    """
    # st.iframe reemplaza a st.components.v1.html a partir de junio de 2026.
    # Se intenta el nuevo primero y se cae al anterior en versiones viejas.
    try:
        st.iframe(PWA_SNIPPET, height=1, width=1)
        return
    except Exception:
        pass
    try:
        import streamlit.components.v1 as components

        components.html(PWA_SNIPPET, height=0, width=0)
    except Exception:
        pass


def page_config() -> None:
    icon = STATIC / "logo.png"
    st.set_page_config(
        page_title=f"{APP_NAME} · {ORG_NAME}",
        page_icon=str(icon) if icon.exists() else "🦁",
        layout="wide",
        initial_sidebar_state="collapsed",
    )


def inject_css() -> None:
    c = COLORS
    st.markdown(
        f"""
<meta name="theme-color" content="{c['bg']}">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Asistencia RDP">
<meta name="mobile-web-app-capable" content="yes">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">

<style>
  html, body, [class*="css"] {{
      -webkit-tap-highlight-color: transparent;
  }}

  .block-container {{
      padding-top: 1.2rem;
      padding-bottom: 4rem;
      max-width: 1280px;
  }}

  /* ---------- Encabezado ---------- */
  .rdp-header {{
      display: flex; align-items: center; gap: .9rem;
      padding: .85rem 1.1rem; margin-bottom: 1.1rem;
      background: linear-gradient(135deg, {c['surface']} 0%, {c['bg']} 100%);
      border: 1px solid {c['border']}; border-radius: 16px;
  }}
  .rdp-header img {{ width: 46px; height: 46px; border-radius: 12px; flex: 0 0 auto; }}
  .rdp-header .t1 {{ font-size: 1.02rem; font-weight: 700; line-height: 1.15; color: {c['text']}; }}
  .rdp-header .t2 {{ font-size: .78rem; color: {c['muted']}; letter-spacing: .02em; }}
  .rdp-header .spacer {{ flex: 1 1 auto; }}
  .rdp-header .who {{ text-align: right; font-size: .78rem; color: {c['muted']}; }}
  .rdp-header .who b {{ display: block; color: {c['text']}; font-size: .9rem; }}

  /* ---------- Reloj ---------- */
  .rdp-clock {{
      text-align: center; padding: 1.4rem 1rem 1.1rem;
      background: {c['surface']}; border: 1px solid {c['border']}; border-radius: 20px;
  }}
  .rdp-clock .hh {{
      font-size: clamp(2.6rem, 11vw, 4.2rem); font-weight: 800;
      letter-spacing: -.02em; line-height: 1; color: {c['text']};
      font-variant-numeric: tabular-nums;
  }}
  .rdp-clock .dd {{ margin-top: .45rem; font-size: .92rem; color: {c['muted']}; }}
  .rdp-clock .tzz {{ margin-top: .15rem; font-size: .72rem; color: {c['muted']}; opacity: .75; }}

  /* ---------- Tarjetas ---------- */
  .rdp-card {{
      background: {c['surface']}; border: 1px solid {c['border']};
      border-radius: 16px; padding: 1rem 1.15rem; margin-bottom: .8rem;
  }}
  .rdp-card h4, .rdp-card-title {{
      margin: 0 0 .5rem 0; font-size: .78rem; letter-spacing: .09em;
      text-transform: uppercase; color: {c['muted']}; font-weight: 700; }}

  /* Contenedor con borde de Streamlit, con la paleta de la organización */
  [data-testid="stVerticalBlockBorderWrapper"] {{
      border-radius: 16px; border-color: {c['border']} !important;
      background: {c['surface']};
  }}

  .rdp-stat {{
      background: {c['surface']}; border: 1px solid {c['border']};
      border-radius: 16px; padding: .9rem 1rem; height: 100%;
  }}
  .rdp-stat .lbl {{ font-size: .72rem; text-transform: uppercase; letter-spacing: .08em;
                    color: {c['muted']}; font-weight: 700; }}
  .rdp-stat .val {{ font-size: 1.75rem; font-weight: 800; line-height: 1.1; margin-top: .2rem;
                    font-variant-numeric: tabular-nums; }}
  .rdp-stat .sub {{ font-size: .74rem; color: {c['muted']}; margin-top: .15rem; }}

  /* ---------- Etiquetas de estado ---------- */
  .rdp-badge {{
      display: inline-flex; align-items: center; gap: .35rem;
      padding: .22rem .65rem; border-radius: 999px;
      font-size: .74rem; font-weight: 700; letter-spacing: .01em;
  }}
  .rdp-dot {{ width: .5rem; height: .5rem; border-radius: 999px; display: inline-block; }}

  /* ---------- Botones ---------- */
  .stButton > button {{
      border-radius: 14px; font-weight: 700; border: 1px solid {c['border']};
      transition: transform .05s ease, filter .15s ease;
  }}
  .stButton > button:active {{ transform: scale(.985); }}
  .stButton > button[kind="primary"] {{
      background: {c['primary']}; color: #17130A; border: none;
      min-height: 3.4rem; font-size: 1.02rem;
  }}
  .stButton > button[kind="primary"]:hover {{ background: {c['primary_d']}; color: #17130A; }}

  .stDownloadButton > button {{ border-radius: 14px; font-weight: 700; min-height: 3rem; }}

  /* ---------- Aviso ---------- */
  .rdp-note {{
      border-radius: 14px; padding: .75rem .95rem; font-size: .86rem;
      border: 1px solid; line-height: 1.45;
  }}

  /* ---------- Móvil ---------- */
  @media (max-width: 640px) {{
      .block-container {{ padding-left: .8rem; padding-right: .8rem; padding-top: .6rem; }}
      .rdp-header {{ gap: .65rem; padding: .7rem .8rem; }}
      .rdp-header img {{ width: 38px; height: 38px; }}
      .rdp-header .t1 {{ font-size: .92rem; }}
      .rdp-header .who {{ font-size: .7rem; }}
      .stButton > button[kind="primary"] {{ min-height: 3.8rem; font-size: 1.06rem; }}
      .rdp-stat .val {{ font-size: 1.45rem; }}
  }}

  /* Ocultar el pie de página por defecto de Streamlit */
  footer {{ visibility: hidden; }}
  #MainMenu {{ visibility: hidden; }}

  /* El iframe de 1 píxel que instala el manifiesto de la PWA no debe ocupar espacio */
  iframe[height="1"] {{ display: none !important; }}
  .stIFrame:has(iframe[height="1"]) {{ display: none !important; }}
  .stCustomComponentV1[height="1"] {{ display: none !important; }}
</style>
""",
        unsafe_allow_html=True,
    )


def header(user_name: str = "", role_label: str = "") -> None:
    logo = logo_data_uri()
    img = f'<img src="{logo}" alt="logo">' if logo else ""
    who = ""
    if user_name:
        who = f'<div class="who"><b>{user_name}</b>{role_label}</div>'
    st.markdown(
        f"""
<div class="rdp-header">
  {img}
  <div>
    <div class="t1">{ORG_NAME}</div>
    <div class="t2">{APP_NAME}</div>
  </div>
  <div class="spacer"></div>
  {who}
</div>
""",
        unsafe_allow_html=True,
    )


def badge(status: str) -> str:
    color = STATUS_COLORS.get(status, COLORS["muted"])
    label = STATUS_LABELS.get(status, status)
    return (
        f'<span class="rdp-badge" style="background:{color}22;color:{color};">'
        f'<span class="rdp-dot" style="background:{color}"></span>{label}</span>'
    )


def stat(label: str, value: str, sub: str = "", color: str | None = None) -> str:
    color = color or COLORS["text"]
    sub_html = f'<div class="sub">{sub}</div>' if sub else ""
    return (
        f'<div class="rdp-stat"><div class="lbl">{label}</div>'
        f'<div class="val" style="color:{color}">{value}</div>{sub_html}</div>'
    )


def note(text: str, kind: str = "info") -> str:
    color = {
        "info": COLORS["info"],
        "ok": COLORS["success"],
        "warn": COLORS["warning"],
        "error": COLORS["danger"],
    }.get(kind, COLORS["info"])
    return (
        f'<div class="rdp-note" style="border-color:{color}55;background:{color}14;'
        f'color:{COLORS["text"]}">{text}</div>'
    )


@contextmanager
def card(title: str = ""):
    """Tarjeta con borde que sí contiene lo que va adentro.

    Se usa el contenedor nativo de Streamlit en lugar de HTML suelto: al
    inyectar un <div> abierto con st.markdown, Streamlit lo cierra solo y
    el contenido terminaba fuera del recuadro.
    """
    caja = st.container(border=True)
    with caja:
        if title:
            st.markdown(f'<div class="rdp-card-title">{title}</div>',
                        unsafe_allow_html=True)
        yield caja
