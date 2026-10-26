import streamlit as st
import pandas as pd
import io
from datetime import date, timedelta
import sys, os, subprocess

import plotly.graph_objects as go

from db import get_historical_rain  # function ใหม่ใน db.py


from theme import apply_theme
apply_theme()

st.markdown("""
<div class="hero-banner">
    <div class="hero-left">
        <p class="eyebrow">Thailand Historical Weather</p>
        <h1 style="font-size:32px;">Historical Rain Report</h1>
        <p class="hero-sub">Actual rain data by district — select a date, province, and hour to explore.</p>
    </div>
    <div class="date-badge" style="min-width:120px;">
        <p>Data source</p>
        <strong>Open-Meteo</strong>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Filters ──
col1, col2, col3 = st.columns([2, 3, 2])

with col1:
    selected_date = st.date_input(
        "Selected Date",
        value=date.today() - timedelta(days=1),
        max_value=date.today(),
    )

# โหลดรายชื่อจังหวัดจาก provinces.json
import json
PROVINCES_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'provinces.json')
with open(PROVINCES_PATH, encoding='utf-8') as f:
    provinces_data = json.load(f)
province_names = sorted([p["province"] for p in provinces_data])

with col2:
    selected_province = st.selectbox(
        "Select Province",
        options=["All Provinces"] + province_names,
    )

with col3:
    hour_options = ["All Hours"] + [f"{h:02d}:00" for h in range(0, 24)]
    selected_hour = st.selectbox("Select Time (Hour)", options=hour_options)

# ── Fetch Button ──
col_btn1, col_btn2, _ = st.columns([2, 2, 4])
with col_btn1:
    fetch_now = st.button("Fetch Data", use_container_width=True, type="secondary")
with col_btn2:
    load_report = st.button("Load Report", use_container_width=True, type="secondary")

if fetch_now:
    st.info("Historical ingestion from the legacy UI is retired. Existing reports remain readable. Use the V2 application for current forecasts; archive lookups require a separately approved on-demand adapter.")

# ── Display name mapping ──
COLUMN_DISPLAY_NAMES = {
    "province":           "Province",
    "district":           "District",
    "rain_status":        "Rain Status",
    "precip_sum_mm":      "Total Rainfall (mm)",
    "temp_max_c":         "Max Temperature (°C)",
    "temp_min_c":         "Min Temperature (°C)",
    "wind_max_kmh":       "Max Wind Speed (km/h)",
    "rainy_hours_detail": "Rainy Hours",
}

# ── Load & Display Report ──
if load_report or "rain_df" in st.session_state:

    if load_report:
        with st.spinner("Loading data..."):
            df = get_historical_rain(
                selected_date=selected_date,
                province=None if selected_province == "All Provinces" else selected_province,
                hour=None if selected_hour == "All Hours" else int(selected_hour[:2]),
            )
            st.session_state["rain_df"] = df
            st.session_state["rain_meta"] = {
                "date": selected_date, "province": selected_province, "hour": selected_hour
            }

    df = st.session_state.get("rain_df", pd.DataFrame())

    if not df.empty:
        df = df[df["district"] != "(Province Level)"]

    meta = st.session_state.get("rain_meta", {})

    if df.empty:
        st.warning("No data found for the selected criteria.")
    else:
        st.markdown("<div style='margin-top: 2rem;'></div>", unsafe_allow_html=True)
        # KPIs
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Locations Found", len(df))
        k2.metric("Max Rainfall (mm)", f"{df['precip_sum_mm'].max():.1f}")
        k3.metric("Avg Rainfall (mm)", f"{df['precip_sum_mm'].mean():.1f}")
        k4.metric("Max Temperature (°C)", f"{df['temp_max_c'].max():.1f}" if 'temp_max_c' in df else "-")

        st.markdown("---")

        # ── Chart: Plotly horizontal bar ──
        is_all_provinces = (selected_province == "All Provinces")
        chart_title = "Top 15 Provinces by Rainfall Volume" if is_all_provinces else f"Top 15 Districts in {selected_province} by Rainfall Volume"
        
        st.markdown(f"""
        <div class="section-card-header" style="margin-bottom: 16px;">
            <h3>{chart_title}</h3>
        </div>
        """, unsafe_allow_html=True)

        # Aggregate data appropriately
        group_col = "province" if is_all_provinces else "district"
        chart_data = (
            df.groupby(group_col, as_index=False)["precip_sum_mm"]
            .sum()
            .sort_values("precip_sum_mm", ascending=False)
            .head(15)
        )
        # Sort ascending for horizontal bar (highest at top)
        chart_data = chart_data.sort_values("precip_sum_mm", ascending=True)

        fig = go.Figure(go.Bar(
            x=chart_data["precip_sum_mm"],
            y=chart_data[group_col],
            orientation="h",
            marker=dict(
                color=chart_data["precip_sum_mm"],
                colorscale=[
                    [0.0, "#BBF7D0"],
                    [0.4, "#1D9E75"],
                    [0.7, "#F97316"],
                    [1.0, "#EF4444"],
                ],
                showscale=False,
            ),
            text=chart_data["precip_sum_mm"].round(1).astype(str) + " mm",
            textposition="outside",
            hovertemplate="<b>%{y}</b><br>Total Rainfall: %{x:.1f} mm<extra></extra>",
        ))

        fig.update_layout(
            xaxis_title="Total Rainfall (mm)",
            yaxis_title=None,
            margin=dict(l=10, r=60, t=10, b=40),
            height=max(300, len(chart_data) * 32),
            plot_bgcolor="white",
            paper_bgcolor="white",
            font=dict(family="Inter, sans-serif", size=12, color="#0F172A"),
            xaxis=dict(
                gridcolor="#E2E8F0",
                gridwidth=1,
                zeroline=False,
            ),
            yaxis=dict(
                gridcolor="#F8FAFF",
            ),
        )

        st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")

        # ── Full table ──
        st.markdown(f"""
        <div class="section-card-header" style="margin-bottom: 16px;">
            <h3>All Data — {len(df)} records</h3>
        </div>
        """, unsafe_allow_html=True)

        display_cols_raw = ["province", "district", "rain_status", "precip_sum_mm", "temp_max_c", "temp_min_c", "wind_max_kmh", "rainy_hours_detail"]
        display_cols_raw = [c for c in display_cols_raw if c in df.columns]

        # Keep raw df for export (full rainy_hours_detail with mm values)
        df_export = df[display_cols_raw].copy()
        if "rainy_hours_detail" in df_export.columns:
            df_export["rainy_hours_detail"] = df_export["rainy_hours_detail"].apply(
                lambda x: ", ".join(x) if isinstance(x, list) else x
            )

        # Build display df: strip mm detail from rainy_hours, apply display names
        df_display = df[display_cols_raw].copy()

        def _strip_mm(val):
            """Strip (x.xmm) suffix from rainy hours — show only hour tokens."""
            if isinstance(val, list):
                hours = []
                for item in val:
                    # "05:00 (1.2mm)" → "05:00"
                    hours.append(str(item).split(" (")[0].strip())
                return ", ".join(hours)
            elif isinstance(val, str):
                import re
                return re.sub(r"\s*\([^)]*mm\)", "", val).strip()
            return val

        if "rainy_hours_detail" in df_display.columns:
            df_display["rainy_hours_detail"] = df_display["rainy_hours_detail"].apply(_strip_mm)

        def style_status(val):
            if "No Rain" in str(val): return "color: #8a8f98;"
            elif "Light Rain" in str(val): return "color: #7170ff; font-weight: 500;"
            elif "Moderate Rain" in str(val): return "color: #10b981; font-weight: 500;"
            elif "Heavy Rain" in str(val): return "color: #E89558; font-weight: 500;"
            elif "Very Heavy Rain" in str(val): return "color: #EA2143; font-weight: 600;"
            return ""

        # Rename columns for display
        df_display = df_display.rename(columns=COLUMN_DISPLAY_NAMES)
        df_sorted = df_display.sort_values("Total Rainfall (mm)", ascending=False)

        # Apply pandas styler for rain_status color coding
        rain_display_col = COLUMN_DISPLAY_NAMES.get("rain_status", "Rain Status")
        if rain_display_col in df_sorted.columns:
            styler = (
                df_sorted.style.map(style_status, subset=[rain_display_col])
                if hasattr(df_sorted.style, "map")
                else df_sorted.style.applymap(style_status, subset=[rain_display_col])
            )
        else:
            styler = df_sorted

        st.dataframe(
            styler,
            width="stretch",
            height=400,
        )

        st.caption(
            "**Rainy Hours** lists the UTC+7 hours with measurable precipitation "
            "(source field: `rainy_hours_detail`). The full per-hour rainfall amounts "
            "are available in the CSV/Excel export."
        )

        # ── Export Buttons (sidebar) ──────────────────────────────────────────
        with st.sidebar:
            st.markdown("---")
            st.markdown('<p style="font-size:10px; text-transform:uppercase; letter-spacing:0.5px; color:#6B6A63; margin-bottom:8px;">EXPORT DATA</p>', unsafe_allow_html=True)

            # Export uses the raw (full detail) version
            csv_bytes = df_export.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
            filename_base = f"rain_{meta.get('date', selected_date)}_{(meta.get('province', selected_province) or 'all').replace(' ', '_')}"

            st.download_button(
                label="Export CSV",
                data=csv_bytes,
                file_name=f"{filename_base}.csv",
                mime="text/csv",
                use_container_width=True,
            )

            excel_buf = io.BytesIO()
            with pd.ExcelWriter(excel_buf, engine="xlsxwriter") as writer:
                df_export.to_excel(writer, index=False, sheet_name="Rain Report")
                workbook = writer.book
                worksheet = writer.sheets["Rain Report"]
                header_fmt = workbook.add_format({"bold": True, "bg_color": "#EFF6FF", "font_color": "#1E40AF"})
                for col_num, col_name in enumerate(display_cols_raw):
                    worksheet.write(0, col_num, col_name, header_fmt)
                    worksheet.set_column(col_num, col_num, 18)
            excel_buf.seek(0)

            st.download_button(
                label="Export Excel",
                data=excel_buf.read(),
                file_name=f"{filename_base}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
