"""
Export component — CSV and Excel download buttons for the sidebar.
Styled with section label per redesign spec.
FEAT-01: Includes district column when level="district".
"""

import io

import pandas as pd
import streamlit as st


def render_export(data: list[dict], selected_date: str, level: str = "province"):
    """Render CSV and Excel download buttons in the sidebar.

    Args:
        data: List of forecast dicts.
        selected_date: Date string (YYYY-MM-DD) for the filename.
        level: "province" | "district" — controls which columns to export.
    """
    if not data:
        return

    # Build flat DataFrame for export
    rows = []
    for doc in data:
        forecast = doc.get("forecast_3_days", [])
        row = {}

        # Add District column when in district mode
        if level == "district":
            row["District"] = doc.get("district", "")

        row["Province"] = doc.get("province", "")
        row["Region"] = doc.get("region", "")
        row["Rain Prob (%)"] = doc.get("rain_probability", 0)
        row["Chance of Rain Band"] = doc.get("rain_level", "")
        row["Volume (mm)"] = doc.get("rain_volume_mm", 0)
        row["Day+1 Prob"] = forecast[0]["rain_prob"] if len(forecast) > 0 else ""
        row["Day+1 Level"] = forecast[0]["level"] if len(forecast) > 0 else ""
        row["Day+2 Prob"] = forecast[1]["rain_prob"] if len(forecast) > 1 else ""
        row["Day+2 Level"] = forecast[1]["level"] if len(forecast) > 1 else ""
        row["Day+3 Prob"] = forecast[2]["rain_prob"] if len(forecast) > 2 else ""
        row["Day+3 Level"] = forecast[2]["level"] if len(forecast) > 2 else ""

        rows.append(row)

    df = pd.DataFrame(rows)

    # Filename includes level for clarity
    level_suffix = f"_{level}" if level == "district" else ""

    with st.sidebar:
        st.markdown("---")
        st.markdown('<p style="font-size:10px; text-transform:uppercase; letter-spacing:0.5px; color:#6B6A63; margin-bottom:8px;">EXPORT DATA</p>', unsafe_allow_html=True)

        # ── CSV download ──────────────────────────────────────────────
        csv_data = df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button(
            label="📄 Export CSV",
            data=csv_data,
            file_name=f"weather_audit{level_suffix}_{selected_date}.csv",
            mime="text/csv",
            use_container_width=True,
        )

        # ── Excel download ────────────────────────────────────────────
        buffer = io.BytesIO()
        df.to_excel(buffer, index=False, engine="openpyxl")
        st.download_button(
            label="📊 Export Excel",
            data=buffer.getvalue(),
            file_name=f"weather_audit{level_suffix}_{selected_date}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
