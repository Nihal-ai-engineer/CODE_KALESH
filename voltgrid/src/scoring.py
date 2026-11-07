"""
VoltGrid — Scoring Engine
Transparent multi-criteria decision analysis (MCDA) for EV charging site screening.

═══════════════════════════════════════════════════════════════════
SCORING METHODOLOGY — Every calculation explained
═══════════════════════════════════════════════════════════════════

STEP 1: NORMALIZATION
─────────────────────
All raw features are normalized to 0–100 scale using robust min-max:
  • Clip to 2nd–98th percentile (removes extreme outliers)
  • Scale: normalized = (value - min) / (max - min) × 100

STEP 2: DEMAND POTENTIAL (0–100)
────────────────────────────────
  DemandPotential = 0.45 × RoadActivity
                  + 0.30 × CommercialActivity
                  + 0.25 × DwellOpportunity

  This estimates WHERE charging demand is likely highest based on:
  • Road hierarchy (proxy for traffic flow)
  • Commercial POI density (footfall generators)
  • Dwell venues (places people stop for 30+ minutes)

  ⚠ This is NOT predicted sessions/day or actual traffic volume.

STEP 3: COVERAGE GAP (0–100)
────────────────────────────
  CoverageGap = 0.60 × DistanceToNearestCharger (normalized)
              + 0.40 × LowNearbyChargerDensity (inverted)

  Higher = area appears more underserved relative to known chargers.
  ⚠ Depends on completeness of the charger dataset.

STEP 4: PRELIMINARY SITE FEASIBILITY (0–100)
─────────────────────────────────────────────
  Feasibility = 0.60 × RoadAccess (major road present = 100, else 0)
              + 0.40 × ParkingAvailability (normalized parking POI count)

  ⚠ This is PRELIMINARY only. Does NOT include:
     grid capacity, land ownership, zoning, transformer availability,
     land cost, or electrical connection approval.

STEP 5: RECOMMENDATION SCORE (0–100)
─────────────────────────────────────
  RecommendationScore = 0.45 × DemandPotential
                      + 0.35 × CoverageGap
                      + 0.20 × PreliminaryFeasibility

  This is a RELATIVE site-screening score.
  ⚠ NOT profitability probability, utilization prediction, or model confidence.

═══════════════════════════════════════════════════════════════════
"""
import numpy as np
import pandas as pd
import geopandas as gpd
from src.feature_engine import haversine_distance


def normalize_series(series, clip_percentile=True, invert=False):
    """
    Robust min-max normalization to 0–100 scale.
    Uses 2nd and 98th percentiles to reduce extreme outlier skewing.
    """
    if series.empty or series.nunique() <= 1:
        return pd.Series(50.0, index=series.index)
    
    if clip_percentile:
        p_low = series.quantile(0.02)
        p_high = series.quantile(0.98)
        if p_low == p_high:
            p_low = series.min()
            p_high = series.max()
        clipped = series.clip(lower=p_low, upper=p_high)
    else:
        clipped = series
    
    c_min = clipped.min()
    c_max = clipped.max()
    
    if c_max == c_min:
        norm = pd.Series(50.0, index=series.index)
    else:
        norm = (clipped - c_min) / (c_max - c_min) * 100.0
    
    if invert:
        norm = 100.0 - norm
    
    return norm


def compute_scores(gdf, w_demand=0.45, w_gap=0.35, w_feas=0.20):
    """
    Calculate transparent MCDA scores for any city's H3 grid.
    Same formula regardless of city. No fake ML, no circular labels.
    """
    df = gdf.copy()
    
    # ── Normalize spatial indicators ──
    df['norm_road_activity'] = normalize_series(df['road_activity'])
    df['norm_commercial'] = normalize_series(df['commercial_poi_count'])
    df['norm_dwell'] = normalize_series(df['dwell_poi_count'])
    df['norm_dist_to_charger'] = normalize_series(df['nearest_charger_km'])
    df['norm_low_nearby_chargers'] = normalize_series(df['nearby_charger_count'], invert=True)
    df['norm_road_access'] = df['major_road_access'] * 100.0
    df['norm_parking'] = normalize_series(df['parking_poi_count'])
    
    has_roads = df.get('road_data_available', pd.Series([True])).iloc[0]
    has_pois = df.get('poi_data_available', pd.Series([True])).iloc[0]
    has_chargers = df.get('charger_data_available', pd.Series([True])).iloc[0]
    
    # ── Dimension 1: Estimated Demand Potential ──
    w_road_act = 0.45 if has_roads else 0.0
    w_comm = 0.30 if has_pois else 0.0
    w_dwell = 0.25 if has_pois else 0.0
    total_demand_w = w_road_act + w_comm + w_dwell
    
    if total_demand_w > 0:
        df['Demand'] = (
            (w_road_act * df['norm_road_activity'] +
             w_comm * df['norm_commercial'] +
             w_dwell * df['norm_dwell']) / total_demand_w
        ).round(1)
    else:
        df['Demand'] = np.nan
        
    # ── Dimension 3: Preliminary Site Feasibility ──
    w_road_acc = 0.60 if has_roads else 0.0
    w_parking = 0.40 if has_pois else 0.0
    total_feas_w = w_road_acc + w_parking
    
    if total_feas_w > 0:
        df['Feasibility'] = (
            (w_road_acc * df['norm_road_access'] +
             w_parking * df['norm_parking']) / total_feas_w
        ).round(1)
    else:
        df['Feasibility'] = np.nan
    
    # ── Dimension 2: Coverage Gap ──
    if has_chargers:
        df['Coverage'] = (
            0.60 * df['norm_dist_to_charger'] +
            0.40 * df['norm_low_nearby_chargers']
        ).round(1)
    else:
        df['Coverage'] = np.nan

    # ── Final Recommendation Score ──
    w_final_demand = w_demand if not df['Demand'].isna().all() else 0.0
    w_final_gap = w_gap if not df['Coverage'].isna().all() else 0.0
    w_final_feas = w_feas if not df['Feasibility'].isna().all() else 0.0
    
    total_final_w = w_final_demand + w_final_gap + w_final_feas
    
    if total_final_w > 0:
        df['Recommendation_Score'] = (
            (w_final_demand * df['Demand'].fillna(0) +
             w_final_gap * df['Coverage'].fillna(0) +
             w_final_feas * df['Feasibility'].fillna(0)) / total_final_w
        ).round(1)
    else:
        df['Recommendation_Score'] = 0.0
    
    return df


def select_top_candidates(gdf, top_n=3, exclusion_radius_km=1.5):
    """
    Select Top Candidate Zones with greedy spatial separation.
    
    Method:
    1. Sort all cells by Recommendation Score (descending)
    2. Select the highest-scoring cell as Rank #1
    3. Suppress all cells within 1.5 km of Rank #1
    4. Select the next highest-scoring unsuppressed cell as Rank #2
    5. Repeat until top_n candidates are selected
    
    This ensures spatial diversity — candidates are spread across the city.
    """
    sorted_df = gdf.sort_values(by='Recommendation_Score', ascending=False)
    candidates = []
    
    for _, row in sorted_df.iterrows():
        if len(candidates) >= top_n:
            break
        
        c_lat = row['centroid_lat']
        c_lon = row['centroid_lon']
        

        
        # Check spatial separation from existing candidates
        too_close = False
        for existing in candidates:
            dist = haversine_distance(c_lat, c_lon, existing['centroid_lat'], existing['centroid_lon'])
            if dist < exclusion_radius_km:
                too_close = True
                break
        
        if not too_close:
            c_dict = row.to_dict()
            c_dict['rank'] = len(candidates) + 1
            # Generic locality labeling
            c_dict['locality_name'] = f"Zone {len(candidates) + 1}"
            c_dict['locality_desc'] = f"H3 cell {row['h3_index'][:8]}..."
            candidates.append(c_dict)
    
    return candidates


def get_scoring_formulas():
    """Return human-readable scoring formulas for display."""
    return {
        'demand': {
            'name': 'Estimated Demand Potential',
            'formula': '0.45 × RoadActivity + 0.30 × CommercialActivity + 0.25 × DwellOpportunity',
            'range': '0–100',
            'disclaimer': 'Estimates WHERE demand is likely highest. NOT predicted sessions/day.',
            'components': [
                ('Road Activity', 0.45, 'Weighted road length by hierarchy class (OSM)'),
                ('Commercial Activity', 0.30, 'Count of malls, markets, offices, banks (OSM)'),
                ('Dwell Opportunity', 0.25, 'Count of restaurants, cafes, hotels, hospitals (OSM)')
            ]
        },
        'coverage': {
            'name': 'Coverage Gap',
            'formula': '0.60 × DistToNearestCharger + 0.40 × LowNearbyDensity',
            'range': '0–100',
            'disclaimer': 'Higher = more underserved. Depends on charger dataset completeness.',
            'components': [
                ('Distance to Nearest Charger', 0.60, 'Haversine distance to closest known station'),
                ('Low Nearby Density', 0.40, 'Inverse of charger count within 2 km radius')
            ]
        },
        'feasibility': {
            'name': 'Preliminary Site Feasibility',
            'formula': '0.60 × RoadAccess + 0.40 × ParkingAvailability',
            'range': '0–100',
            'disclaimer': 'PRELIMINARY only. Excludes grid capacity, land cost, zoning.',
            'components': [
                ('Road Access', 0.60, 'Major road (trunk/primary/motorway) present in cell'),
                ('Parking Availability', 0.40, 'Count of parking amenities in cell (OSM)')
            ]
        },
        'recommendation': {
            'name': 'Recommendation Score',
            'formula': '0.45 × DemandPotential + 0.35 × CoverageGap + 0.20 × Feasibility',
            'range': '0–100',
            'disclaimer': 'Relative screening score. NOT profitability or utilization prediction.',
            'components': [
                ('Demand Potential', 0.45, 'Estimated charging demand from spatial signals'),
                ('Coverage Gap', 0.35, 'Degree of underservice by existing chargers'),
                ('Preliminary Feasibility', 0.20, 'Physical road access and parking proximity')
            ]
        }
    }
