# ⛈ Weather Advisor — Hyper-Local Thailand Weather Intelligence

**Weather Advisor** is a professional, interactive weather dashboard built to support business operations, logistics, and risk management across Thailand. It provides hyper-local weather intelligence covering **77 provinces** and **913 districts**. It features both **Future Forecasts** and **Historical Analysis**, empowering teams to track real-time conditions, predict weather impacts up to 3 days in advance, and audit past weather events.

---

## 🌟 Key Business Value

- **Hyper-Local Precision (District-Level):** Move beyond broad provincial data. Drill down into 913 specific districts to accurately plan logistics, agricultural activities, or analyze past weather events.
- **Dual Perspective:** Combine **3-Day Forward-Looking Forecasts** with **Historical Rain Auditing** to make well-rounded operational decisions.
- **Visual Intelligence:** Intuitive UI with traffic-light color coding (Green/Amber/Red) for risks and side-by-side maps for instant gap analysis.
- **Seamless Data Integration:** Filter data visually and export it directly to **CSV** or **Excel** with one click for easy integration into your existing BI or reporting tools.

---

## 💻 Product Features & UI Overview

The application is divided into three primary views:

### 1. 🏠 Home Page (New)
*Focus: Fast loading and welcoming entrance*
- **3D Animated Hero:** Features a custom Canvas 2D particle sphere representing a high-tech radar interface.
- **Cache Warm-Up:** Intelligently pre-loads heavy GeoJSON files (over 28MB) and MongoDB connections in the background so dashboards open instantly.

### 2. 🌤 Weather Forecast Dashboard
*Focus: Risk prevention and forward planning (Up to 3 Days)*

- **Executive KPIs & Alerts:** Real-time counters for High Rain Zones and Very Heavy Rain. 
- **Dual Map Analysis:** Two maps rendered side-by-side using PyDeck.
  - 🗺️ **Predicted Daily Rain Map:** Max probability of rain for the day.
  - 📡 **Current Rain Map:** Real-time exact rain volume (mm) falling.
- **Dynamic Auto-Zoom (New):** Maps automatically calculate coordinate spreads and zoom/center onto the specific province or districts you filter.
- **Visual 3-Day Forecast:** Dynamic, color-coded timeline (Day+1, Day+2, Day+3) organized by region.
- **Manual Refresh Button:** Fetches data on-demand. If districts are selected, it fetches *only* those districts in seconds, bypassing the 35-minute nationwide fetch.

### 3. 🌧 Historical Rain Report (Audit Dashboard)
*Focus: Post-event analysis and claims validation*

- **Dynamic Interactive Charts (New):** Utilizes `plotly` to render horizontal bar charts. Automatically switches between "Top 15 Provinces" and "Top 15 Districts" based on your filters.
- **Live Data Fetching:** On-demand data fetching capability directly from the UI.
- **Detailed Data Grid:** Interactive table displaying comprehensive weather metrics, ready for export.

---

## 🚦 Risk Level Classification (Forecasts)

Weather Advisor automatically categorizes risk to simplify decision-making.

| Probability | Rain Level | Actionable Insight | Color Coding |
|---|---|---|---|
| **< 20%** | No Rain | Safe for all outdoor operations. | ⬜ Gray / Transparent |
| **20–39%** | Light Rain | Minor disruptions possible. | 🔵 Blue / Info |
| **40–59%** | Moderate Rain | Prepare for moderate delays. | 🟢 Green / Safe |
| **60–79%** | Heavy Rain | High risk of logistical delays. | 🟠 Amber / Warning |
| **≥ 80%** | Very Heavy Rain | Critical risk. Potential flooding. | 🔴 Red / Danger |

---

## ⚙️ Technical Architecture & Data Pipeline

The platform is designed to be highly automated and maintenance-free, leveraging modern cloud infrastructure.

| Component | Detail |
|-----------|--------|
| **Data Source** | [Open-Meteo API](https://open-meteo.com/) (Free Tier) — Forecast API + Archive API |
| **ETL Scripts** | `etl/fetch_weather.py` (forecast), `etl/backfill.py` (historical) |
| **Database** | MongoDB Atlas — upsert keyed on `{date, province/district, level}` |
| **Automation** | GitHub Actions cron — 08:00 & 13:00 Bangkok time |
| **Frontend** | Streamlit + custom CSS (Sky Palette light theme) |

### Estimated ETL Runtime

| Level | Locations | Estimated Time | Notes |
|-------|-----------|----------------|-------|
| Province | 77 | ~4 min | Nationwide |
| District | 913 | ~35 min | Nationwide |
| Targeted | 1–15 | ~5 seconds | Triggered via UI refresh button |

---

## 🤖 GitHub Actions Automation

Workflow file: `.github/workflows/etl.yml`

```
Cron Schedule (UTC):
  01:00 UTC → Morning round  (08:00 BKK)
  06:00 UTC → Afternoon round (13:00 BKK)
```

**Scheduled (Cron) runs:** fetch Province → then District automatically.  
**Manual (workflow_dispatch) runs:** select level (province / district) individually.

---

## 🚀 Setup & Deployment

### Local Development

1. Clone the repository and activate your Python environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create `.streamlit/secrets.toml` with your MongoDB credentials:
   ```toml
   [mongodb]
   uri        = "mongodb+srv://<user>:<password>@<cluster>.mongodb.net/"
   db_name    = "weather_db"
   collection = "forecasts"
   ```
4. Run the application:
   ```bash
   streamlit run app/main.py
   ```

### Running the ETL Manually

```bash
# Province-level forecast (77 locations)
python etl/fetch_weather.py --round morning --level province

# District-level forecast (913 locations)
python etl/fetch_weather.py --round morning --level district

# Targeted District fetch (super fast, comma-separated)
python etl/fetch_weather.py --round morning --level district --districts "Mueang Chiang Mai,Hang Dong"

# Historical backfill
python etl/backfill.py --level district --days 7
```

### GitHub Actions — First-Time Setup

1. Go to **Settings → Secrets and variables → Actions** and add:
   - `MONGODB_URI`
   - `MONGODB_DB_NAME`
   - `MONGODB_COLLECTION`
2. Go to **Actions tab** → enable workflows if prompted.
3. Trigger a manual run: `Actions → Weather ETL → Run workflow`.

> **Note:** MongoDB Atlas Network Access must allow `0.0.0.0/0` for GitHub Actions runners (dynamic IPs).

---

*Disclaimer: Weather data is sourced from meteorological models and represents probabilities. Accuracy varies, especially for D+2 and D+3 forecasts.*
