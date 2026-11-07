# ⚡ VoltGrid — EV Infrastructure Intelligence for India

> **Find where charging infrastructure should go next.**

VoltGrid is a nationwide EV infrastructure decision-support platform. It uses real geospatial data to screen Indian cities for charging-demand potential, existing infrastructure gaps, and preliminary site feasibility. AI interprets spatial signals and turns them into actionable site assessments, while clearly identifying what still requires real-world verification.

---

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

---

## 🏗️ Architecture

```
voltgrid/
├── app.py                    # Multi-page Streamlit application
├── requirements.txt
├── README.md
│
├── data/
│   ├── india/
│   │   └── city_index.json   # National city registry
│   └── chandigarh/           # Offline-ready pilot city
│       ├── boundary.geojson  # OSM administrative boundary
│       ├── roads.gpkg        # Real OSM road network
│       ├── pois.gpkg         # Real OSM points of interest
│       ├── chargers.json     # 25 curated real charger locations
│       ├── metadata.json     # Data provenance & completeness
│       └── analysis_cache.json
│
└── src/
    ├── city_resolver.py      # City lookup, boundary resolution, OSMnx
    ├── data_manager.py       # Orchestrates full analysis pipeline
    ├── osm_fetcher.py        # Fetches roads/POIs from OpenStreetMap
    ├── charger_loader.py     # Loads real charger data per city
    ├── h3_engine.py          # Generates H3 hexagonal spatial grid
    ├── feature_engine.py     # Extracts road/POI/charger features
    ├── scoring.py            # MCDA scoring (demand, coverage, feasibility)
    ├── ai_demand.py          # AI Demand Outlook (Gemma / deterministic)
    └── ai_analyst.py         # AI Site Analyst (Gemma / deterministic)
```

---

## 📐 Scoring Methodology

### Demand Potential (0–100)
```
DemandPotential = 0.45 × RoadActivity + 0.30 × CommercialActivity + 0.25 × DwellOpportunity
```
Estimates WHERE demand is likely highest. **NOT** predicted sessions/day.

### Coverage Gap (0–100)
```
CoverageGap = 0.60 × DistToNearestCharger + 0.40 × LowNearbyChargerDensity
```
Higher = more underserved. Depends on charger dataset completeness.

### Preliminary Feasibility (0–100)
```
Feasibility = 0.60 × RoadAccess + 0.40 × ParkingAvailability
```
**Preliminary only.** Excludes grid capacity, land ownership, zoning.

### Recommendation Score (0–100)
```
RecommendationScore = 0.45 × DemandPotential + 0.35 × CoverageGap + 0.20 × Feasibility
```
Relative site-screening score. **NOT** profitability or utilization prediction.

---

## 🗃️ Data Sources

| Layer | Source | Status |
|:------|:-------|:-------|
| Road Network | OpenStreetMap (OSMnx) | ✓ Real geometry |
| Points of Interest | OpenStreetMap (OSMnx) | ✓ Real spatial nodes |
| Spatial Grid | Uber H3 Index | ✓ Resolution 9 (~0.1 km²) |
| EV Chargers | Curated Reference Dataset | ✓ 25 real stations (Chandigarh) |
| Traffic | Road hierarchy classification | ⚠️ Proxy only |
| Grid Capacity | — | ❌ Not included |
| Land Price | — | ❌ Not included |
| AI Assessment | Gemma-3 via LM Studio | ✓ Local qualitative assessment |

---

## 🤖 AI Configuration

### LM Studio Setup (Optional)
1. Install [LM Studio](https://lmstudio.ai/)
2. Download `google/gemma-3-12b` model
3. Start the local server on port 1234

If LM Studio is not running, VoltGrid automatically falls back to a deterministic rules engine.

---

## 📍 Cached Cities

| City | Status | Chargers | H3 Cells |
|:-----|:-------|:---------|:---------|
| Chandigarh | ✅ Offline Ready | 25 | 1,031 |

Any other Indian city can be analysed on-demand via "Generate Analysis" (requires internet).

---

## ⚠️ Known Limitations

- Traffic volume is approximated via road hierarchy — not real sensor data
- Coverage gap depends on completeness of the charger dataset
- Feasibility is preliminary — grid capacity, land cost, and zoning require field verification
- No supervised ML model is included (no real training labels available)
- AI assessments are qualitative — not statistical predictions

---

## 🚫 What VoltGrid Does NOT Do

- Does not predict charger utilization or sessions/day
- Does not estimate revenue, ROI, or payback period automatically
- Does not invent charger locations or fabricate city data
- Does not claim model confidence or statistical probability
- Does not include grid capacity or land ownership analysis
