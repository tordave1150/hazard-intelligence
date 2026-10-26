"""
Theme module — "Dashboard" design system (open-design/design-systems/dashboard).

Cloud-platform aesthetic: cool surfaces, sky-blue accent (#0ea5e9),
Inter body + IBM Plex Mono mono, raised glass-like panels, status-first
data hierarchy. Inspired by Vercel/GitHub/Heroku-style dashboards.

Design tokens sourced from:
    open-design/design-systems/dashboard/tokens.css

Usage:
    from theme import apply_theme, get_hero_gradient, get_alert_level
    apply_theme()  # call once at the top of each page
"""

import streamlit as st


# ── Design System Tokens ────────────────────────────────────────────────

THEME = {
    # Base surfaces
    "bg_page":      "#f4f7fb",   # cool blue-grey page background
    "bg_card":      "#ffffff",
    "bg_card_warm": "#eef6ff",   # warm surface for KPI cards
    "bg_sidebar":   "#eef6ff",
    "bg_header":    "linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%)",

    # Text
    "text_primary":   "#111827",  # near-black
    "text_secondary": "#334155",
    "text_muted":     "#64748b",
    "text_on_hero":   "#ffffff",

    # Accent
    "accent":       "#0ea5e9",   # sky blue — primary interaction signal
    "accent_hover": "#0284c7",

    # Border
    "border":       "#d8e2ee",   # cool, less saturated
    "border_soft":  "#edf3f8",

    # Elevation
    "elev_raised":  "0 18px 46px rgba(15, 23, 42, 0.10)",
    "elev_ring":    "0 0 0 1px #d8e2ee",

    # Semantic colours
    "success":      "#10b981",
    "warn":         "#f59e0b",
    "danger":       "#ef4444",

    # Rain level badge colors
    "no_rain":       {"bg": "#F0FDF4", "text": "#166534", "border": "#86EFAC"},
    "light_rain":    {"bg": "#ECFDF5", "text": "#065F46", "border": "#6EE7B7"},
    "moderate_rain": {"bg": "#FFF7ED", "text": "#9A3412", "border": "#FED7AA"},
    "heavy_rain":    {"bg": "#FFF1F2", "text": "#881337", "border": "#FECDD3"},
    "very_heavy":    {"bg": "#EDE9FE", "text": "#4C1D95", "border": "#C4B5FD"},

    # Map dot colors (README spec)
    "map_green":  [34, 197, 94],     # < 40%
    "map_yellow": [250, 204, 21],    # 40–59%
    "map_orange": [249, 115, 22],    # 60–79%
    "map_red":    [239, 68, 68],     # ≥ 80%
}


# ── Global CSS Injection ────────────────────────────────────────────────

def apply_theme() -> None:
    """Inject global CSS for the open-design Dashboard design system.

    Applies cloud-platform aesthetics: cool #f4f7fb background, sky-blue
    #0ea5e9 accent, IBM Plex Mono for mono/eyebrow text, Inter for body,
    raised panel shadows, and 8pt baseline grid spacing.

    Call once at the top of each page, right after st.set_page_config()
    or at the start of a page script.
    """
    st.markdown("""
    <style>
    /* ── Google Fonts — Inter + IBM Plex Mono ── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;700&display=swap');

    /* ── CSS Tokens ── */
    :root {
        --bg:            #f4f7fb;
        --surface:       #ffffff;
        --surface-warm:  #eef6ff;
        --fg:            #111827;
        --fg-2:          #334155;
        --muted:         #64748b;
        --accent:        #0ea5e9;
        --accent-hover:  #0284c7;
        --border:        #d8e2ee;
        --border-soft:   #edf3f8;
        --success:       #10b981;
        --warn:          #f59e0b;
        --danger:        #ef4444;
        --radius-sm:     8px;
        --radius-md:     12px;
        --radius-lg:     18px;
        --radius-pill:   9999px;
        --elev-raised:   0 18px 46px rgba(15, 23, 42, 0.10);
        --elev-ring:     0 0 0 1px var(--border);
        --focus-ring:    0 0 0 4px rgba(14, 165, 233, 0.22);
        --motion-fast:   120ms;
        --motion-base:   200ms;
        --ease:          cubic-bezier(0.2, 0, 0, 1);
        --font-body:     'Inter', system-ui, sans-serif;
        --font-mono:     'IBM Plex Mono', ui-monospace, Menlo, monospace;
    }

    /* ── Reset & Base ── */
    *, *::before, *::after { box-sizing: border-box; }

    /* ── Page background ── */
    .stApp {
        background: var(--bg) !important;
    }
    [data-testid="stAppViewContainer"] {
        background: var(--bg) !important;
        font-family: var(--font-body) !important;
    }
    .block-container {
        padding-top: 3.5rem !important;
        padding-bottom: 2rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        max-width: 1400px !important;
    }

    /* ── Global font ── */
    html, body, [class*="css"] {
        font-family: var(--font-body) !important;
        -webkit-font-smoothing: antialiased;
    }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background: var(--surface-warm) !important;
        border-right: 1px solid var(--border) !important;
    }
    [data-testid="stSidebar"] * { color: var(--fg) !important; }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        font-size: 13px;
        color: var(--muted) !important;
    }
    [data-testid="stSidebar"] .stMultiSelect [data-baseweb="tag"] {
        background: #dbeafe !important;
        color: #1e40af !important;
        border-radius: var(--radius-pill) !important;
        font-size: 11px !important;
        border: 1px solid #93c5fd !important;
    }

    /* ── KPI metric cards — raised panel style ── */
    [data-testid="stMetric"] {
        background: var(--surface) !important;
        border: 1px solid var(--border) !important;
        border-top: 2px solid var(--accent) !important;
        border-radius: var(--radius-md) !important;
        padding: 16px 20px !important;
        box-shadow: var(--elev-raised) !important;
        transition: box-shadow var(--motion-fast) var(--ease) !important;
    }
    [data-testid="stMetric"]:hover {
        box-shadow: 0 24px 56px rgba(15, 23, 42, 0.14) !important;
    }
    [data-testid="stMetricLabel"] {
        color: var(--muted) !important;
        font-size: 11px !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.08em !important;
        font-family: var(--font-mono) !important;
    }
    [data-testid="stMetricValue"] {
        color: var(--fg) !important;
        font-size: 1.85rem !important;
        font-weight: 700 !important;
        letter-spacing: -0.015em !important;
        font-variant-numeric: tabular-nums !important;
    }
    [data-testid="stMetricDelta"] {
        font-size: 12px !important;
        font-family: var(--font-mono) !important;
    }

    /* ── Data table ── */
    [data-testid="stDataFrame"] {
        background: var(--surface) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius-md) !important;
        overflow: hidden !important;
    }
    [data-testid="stDataFrame"] table { color: var(--fg) !important; }
    [data-testid="stDataFrame"] thead th {
        background: var(--surface-warm) !important;
        color: var(--accent) !important;
        font-weight: 700 !important;
        font-size: 11px !important;
        text-transform: uppercase !important;
        letter-spacing: 0.08em !important;
        font-family: var(--font-mono) !important;
    }
    [data-testid="stDataFrame"] tbody tr:nth-child(odd) {
        background: #f9fbfd !important;
    }
    [data-testid="stDataFrame"] tbody tr:hover {
        background: var(--surface-warm) !important;
    }

    /* ── Expander ── */
    [data-testid="stExpander"] {
        background: var(--surface) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius-md) !important;
        margin-bottom: 6px !important;
        box-shadow: var(--elev-ring) !important;
        transition: box-shadow var(--motion-fast) var(--ease) !important;
    }
    [data-testid="stExpander"]:hover {
        box-shadow: 0 4px 12px rgba(14, 165, 233, 0.10) !important;
    }
    [data-testid="stExpander"] summary {
        color: var(--fg) !important;
        font-weight: 600 !important;
        font-size: 14px !important;
    }

    /* ── Buttons ── */
    .stButton > button,
    [data-testid="stSidebar"] .stButton > button {
        background: var(--accent) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: var(--radius-sm) !important;
        font-weight: 700 !important;
        font-size: 13px !important;
        min-height: 40px !important;
        transition:
            background-color var(--motion-fast) var(--ease),
            transform var(--motion-fast) var(--ease),
            box-shadow var(--motion-fast) var(--ease) !important;
    }
    .stButton > button *,
    [data-testid="stSidebar"] .stButton > button * {
        color: #ffffff !important;
    }
    .stButton > button:hover,
    [data-testid="stSidebar"] .stButton > button:hover {
        background: var(--accent-hover) !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(14, 165, 233, 0.30) !important;
    }
    .stButton > button:hover *,
    [data-testid="stSidebar"] .stButton > button:hover * {
        color: #ffffff !important;
    }
    .stButton > button:focus-visible {
        outline: none !important;
        box-shadow: var(--focus-ring) !important;
    }
    .stButton > button[data-testid="baseButton-tertiary"] {
        background: var(--surface) !important;
        color: var(--fg) !important;
        border: 1px solid var(--border) !important;
        box-shadow: var(--elev-ring) !important;
    }
    .stButton > button[data-testid="baseButton-tertiary"] * {
        color: var(--fg) !important;
    }
    .stButton > button[data-testid="baseButton-tertiary"]:hover {
        border-color: var(--accent) !important;
        color: var(--accent) !important;
        transform: translateY(-1px) !important;
    }
    .stButton > button[data-testid="baseButton-tertiary"]:hover * {
        color: var(--accent) !important;
    }

    /* ── Download buttons ── */
    .stDownloadButton > button,
    [data-testid="stSidebar"] .stDownloadButton > button {
        background: var(--surface) !important;
        color: var(--accent) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius-sm) !important;
        font-size: 13px !important;
        font-weight: 600 !important;
        width: 100% !important;
        transition: border-color var(--motion-fast) var(--ease),
                    transform var(--motion-fast) var(--ease) !important;
    }
    .stDownloadButton > button *,
    [data-testid="stSidebar"] .stDownloadButton > button * {
        color: var(--accent) !important;
    }
    .stDownloadButton > button:hover,
    [data-testid="stSidebar"] .stDownloadButton > button:hover {
        border-color: var(--accent) !important;
        background: var(--surface-warm) !important;
        transform: translateY(-1px) !important;
    }
    .stDownloadButton > button:hover *,
    [data-testid="stSidebar"] .stDownloadButton > button:hover * {
        color: var(--accent) !important;
    }

    /* ── Section headers ── */
    h1, h2, h3 {
        color: var(--fg) !important;
        letter-spacing: -0.015em !important;
        line-height: 1.1 !important;
    }
    h1 { font-size: 1.4rem !important; }
    h2 {
        font-size: 1.1rem !important;
        border-bottom: 1px solid var(--border-soft);
        padding-bottom: 6px;
    }

    /* ── Alert / info boxes ── */
    [data-testid="stAlert"] {
        background: #fffbeb !important;
        border-left: 4px solid var(--warn) !important;
        color: #78350f !important;
        border-radius: 0 var(--radius-sm) var(--radius-sm) 0 !important;
    }

    /* ── Selectbox / MultiSelect / TextInput / DateInput ── */
    [data-testid="stSelectbox"] > div > div,
    [data-testid="stMultiSelect"] > div > div,
    [data-testid="stTextInput"] > div > div,
    [data-testid="stDateInput"] > div > div {
        background: var(--surface) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius-sm) !important;
        color: var(--fg) !important;
        transition: border-color var(--motion-fast) var(--ease) !important;
    }
    [data-testid="stSelectbox"] > div > div:focus-within,
    [data-testid="stMultiSelect"] > div > div:focus-within,
    [data-testid="stTextInput"] > div > div:focus-within,
    [data-testid="stDateInput"] > div > div:focus-within {
        border-color: var(--accent) !important;
        box-shadow: var(--focus-ring) !important;
    }

    /* ── Map container ── */
    iframe { border-radius: var(--radius-md) !important; }

    /* ── Custom scrollbar ── */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: var(--bg); }
    ::-webkit-scrollbar-thumb {
        background: #cbd5e1;
        border-radius: var(--radius-pill);
    }
    ::-webkit-scrollbar-thumb:hover { background: var(--accent); }

    /* ── Eyebrow label (IBM Plex Mono, accent, uppercase) ── */
    .eyebrow {
        color: var(--accent);
        font-family: var(--font-mono);
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        margin: 0 0 6px 0;
    }

    /* ── Hero banner — Dashboard panel style ── */
    .hero-banner {
        background: var(--surface);
        border: 1px solid var(--border);
        border-top: 3px solid var(--accent);
        border-radius: var(--radius-lg);
        padding: 24px 32px;
        color: var(--fg);
        margin-bottom: 24px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: var(--elev-raised);
    }
    .hero-banner .eyebrow {
        font-size: 11px;
        letter-spacing: 0.12em;
        color: var(--accent);
        font-family: var(--font-mono);
        font-weight: 700;
        margin: 0 0 8px 0;
        text-transform: uppercase;
    }
    .hero-banner h1 {
        font-size: 40px;
        font-weight: 700;
        margin: 0 0 8px 0;
        color: var(--fg);
        letter-spacing: -0.015em;
        line-height: 1.0;
    }
    .hero-banner .hero-sub {
        font-size: 15px;
        color: var(--fg-2);
        margin: 0;
    }
    .hero-banner .date-badge {
        background: var(--surface-warm);
        border: 1px solid var(--border);
        border-radius: var(--radius-md);
        padding: 12px 20px;
        text-align: center;
    }
    .hero-banner .date-badge p {
        font-size: 11px;
        font-weight: 700;
        color: var(--muted);
        margin: 0 0 4px 0;
        font-family: var(--font-mono);
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }
    .hero-banner .date-badge strong {
        font-size: 18px;
        font-weight: 700;
        color: var(--fg);
        letter-spacing: -0.015em;
    }

    /* ── Status pill (live indicator) ── */
    .status-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        color: var(--accent);
        font-family: var(--font-mono);
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }
    .status-pill::before {
        content: "";
        width: 8px;
        height: 8px;
        border-radius: var(--radius-pill);
        background: #10b981;
        display: inline-block;
        animation: pulse-dot 2s infinite;
    }
    @keyframes pulse-dot {
        0%, 100% { opacity: 1; transform: scale(1); }
        50%       { opacity: 0.6; transform: scale(0.85); }
    }

    /* ── Alert bar ── */
    .alert-bar {
        border-radius: var(--radius-md);
        padding: 12px 16px;
        font-size: 14px;
        margin-bottom: 24px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .alert-bar.alert-warning {
        background: #fffbeb;
        border: 1px solid #fde68a;
        color: #78350f;
    }
    .alert-bar.alert-critical {
        background: #fef2f2;
        border: 1px solid #fecaca;
        color: #7f1d1d;
    }

    /* ── Rain level badges ── */
    .badge-no-rain {
        background: #F0FDF4; color: #166534;
        border-radius: var(--radius-pill); padding: 2px 10px;
        border: 1px solid #86EFAC; font-size: 12px;
        font-weight: 600; display: inline-block;
        font-family: var(--font-mono);
    }
    .badge-light {
        background: #ECFDF5; color: #065F46;
        border-radius: var(--radius-pill); padding: 2px 10px;
        border: 1px solid #6EE7B7; font-size: 12px;
        font-weight: 600; display: inline-block;
        font-family: var(--font-mono);
    }
    .badge-moderate {
        background: #FFF7ED; color: #9A3412;
        border-radius: var(--radius-pill); padding: 2px 10px;
        border: 1px solid #FED7AA; font-size: 12px;
        font-weight: 600; display: inline-block;
        font-family: var(--font-mono);
    }
    .badge-heavy {
        background: #FFF1F2; color: #881337;
        border-radius: var(--radius-pill); padding: 2px 10px;
        border: 1px solid #FECDD3; font-size: 12px;
        font-weight: 600; display: inline-block;
        font-family: var(--font-mono);
    }
    .badge-veryheavy {
        background: #EDE9FE; color: #4C1D95;
        border-radius: var(--radius-pill); padding: 2px 10px;
        border: 1px solid #C4B5FD; font-size: 12px;
        font-weight: 600; display: inline-block;
        font-family: var(--font-mono);
    }

    /* ── Section card wrapper ── */
    .section-card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: var(--radius-lg);
        padding: 0;
        margin-bottom: 24px;
        overflow: hidden;
        box-shadow: var(--elev-raised);
    }
    .section-card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 14px 20px;
        border-bottom: 1px solid var(--border-soft);
        background: var(--surface);
        border-radius: var(--radius-sm);
    }
    .section-card-header h3 {
        font-size: 14px !important;
        font-weight: 700 !important;
        color: var(--fg) !important;
        margin: 0 !important;
        letter-spacing: -0.01em !important;
        border: none !important;
        padding: 0 !important;
    }
    .section-card-header .legend {
        display: flex;
        gap: 12px;
        align-items: center;
        font-size: 12px;
        color: var(--muted);
        font-family: var(--font-mono);
    }
    .section-card-header .legend .dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        display: inline-block;
        margin-right: 4px;
    }
    .section-card-body { padding: 16px 20px; }

    /* ── Forecast day cards ── */
    .forecast-day-card {
        background: var(--surface-warm);
        border-radius: var(--radius-sm);
        border: 1px solid var(--border-soft);
        padding: 12px 14px;
        transition: border-color var(--motion-fast) var(--ease),
                    box-shadow var(--motion-fast) var(--ease);
    }
    .forecast-day-card:hover {
        border-color: var(--accent);
        box-shadow: 0 4px 12px rgba(14, 165, 233, 0.10);
    }
    .forecast-day-card .day-label {
        font-size: 10px;
        font-weight: 700;
        color: var(--muted);
        margin: 0 0 6px 0;
        font-family: var(--font-mono);
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }
    .forecast-day-card .day-value {
        font-size: 13px;
        font-weight: 600;
        color: var(--fg);
        margin: 0;
    }

    /* ── Metric sub-labels ── */
    .metric-sub {
        font-size: 12px;
        color: var(--muted);
        margin-top: 4px;
        font-family: var(--font-mono);
    }
    .metric-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        display: inline-block;
        margin-right: 6px;
        vertical-align: middle;
    }

    /* ── Region header ── */
    .region-header-flat {
        display: flex;
        align-items: center;
        gap: 8px;
        margin: 16px 0 8px 0;
        padding: 8px 14px;
        background: var(--surface-warm);
        border: 1px solid var(--border-soft);
        border-radius: var(--radius-sm);
    }
    .region-header-flat .region-dot-flat {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        display: inline-block;
    }
    .region-header-flat .region-name {
        font-size: 13px;
        font-weight: 700;
        color: var(--fg);
        letter-spacing: -0.01em;
    }
    .region-header-flat .region-count {
        font-size: 11px;
        color: var(--muted);
        font-family: var(--font-mono);
    }

    /* ── List item (province/district in expander) ── */
    .list-item {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 6px 0;
        border-bottom: 1px solid var(--border-soft);
    }
    .list-item:last-child { border-bottom: none; }
    .list-item .loc-name {
        font-size: 14px;
        font-weight: 500;
        color: var(--fg-2);
    }

    /* ── Divider ── */
    hr { border-color: var(--border-soft) !important; }

    /* ── Panel (generic glass-like card) ── */
    .panel {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: var(--radius-lg);
        box-shadow: var(--elev-raised);
        overflow: hidden;
    }
    .panel-head {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 16px;
        padding: 16px 20px;
        border-bottom: 1px solid var(--border-soft);
    }
    </style>
    """, unsafe_allow_html=True)


# ── Weather-Aware Dynamic Theming ───────────────────────────────────────

def get_hero_gradient(rain_prob_avg: float) -> str:
    """Return CSS gradient string based on current weather severity.

    Args:
        rain_prob_avg: Average rain probability across filtered data.

    Returns:
        CSS linear-gradient string.
    """
    if rain_prob_avg < 40:
        # Clear / light — sky blue to cyan
        return "linear-gradient(135deg, #0EA5E9 0%, #38BDF8 50%, #7DD3FC 100%)"
    elif rain_prob_avg < 70:
        # Moderate — blue-grey to slate
        return "linear-gradient(135deg, #1E40AF 0%, #2563EB 50%, #6366F1 100%)"
    else:
        # Heavy / very heavy — deep blue to purple (stormy)
        return "linear-gradient(135deg, #1E1B4B 0%, #312E81 50%, #4C1D95 100%)"


def get_alert_level(very_heavy_count: int) -> dict:
    """Return alert config for dynamic alert bar.

    Alert bar displays when very_heavy_count >= 10 (per README spec).

    Args:
        very_heavy_count: Number of locations with Very Heavy Rain.

    Returns:
        Dict with keys: show, level, color, bg, icon, msg, css_class.
    """
    if very_heavy_count >= 20:
        return {
            "show": True,
            "level": "critical",
            "icon": "🔴",
            "css_class": "alert-critical",
            "msg": f"Critical: {very_heavy_count} provinces with Very Heavy Rain",
        }
    elif very_heavy_count >= 10:
        return {
            "show": True,
            "level": "warning",
            "icon": "⚠️",
            "css_class": "alert-warning",
            "msg": f"Warning: {very_heavy_count} provinces with Very Heavy Rain",
        }
    else:
        return {"show": False}
