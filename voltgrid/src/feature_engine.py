"""
VoltGrid — Feature Engine
Extracts real spatial features from OSM data for any city.
All features come from OpenStreetMap — nothing is fabricated.

═══════════════════════════════════════════════════════════
FEATURE EXTRACTION METHODOLOGY
═══════════════════════════════════════════════════════════

1. ROAD ACTIVITY (proxy for traffic potential)
   ─────────────────────────────────────────────
   For each H3 cell, we measure the total length of roads
   weighted by road hierarchy importance:
   
     road_activity = Σ (segment_length_meters × weight)
   
   Weights:
     motorway  = 1.00  (highest traffic capacity)
     trunk     = 0.95
     primary   = 0.85
     secondary = 0.70
     tertiary  = 0.55
     residential = 0.25
     service   = 0.15  (lowest traffic capacity)
   
   ⚠ This is a PROXY for traffic activity based on road 
   classification. It is NOT actual traffic volume data.

2. COMMERCIAL POIs (footfall proxy)
   ─────────────────────────────────
   Count of OSM features per cell:
     shop = mall | supermarket | department_store
     amenity = marketplace | bank
     office = * (any office)
   
3. DWELL POIs (stop-and-charge opportunity)
   ─────────────────────────────────────────
   Count of OSM features per cell:
     amenity = restaurant | cafe | fast_food | cinema | hospital
     tourism = hotel | attraction
   
4. PARKING POIs (physical charger placement feasibility)
   ─────────────────────────────────────────────────────
   Count of OSM features per cell:
     amenity = parking | parking_space

5. CHARGER PROXIMITY
   ──────────────────
   For each cell centroid:
     nearest_charger_km = haversine distance to closest known charger
     nearby_charger_count = chargers within 2.0 km radius
═══════════════════════════════════════════════════════════
"""
import os
import json
import numpy as np
import pandas as pd
import geopandas as gpd

# Road hierarchy weights — empirical activity proxies (NOT live traffic)
ROAD_WEIGHTS = {
    'motorway': 1.00,
    'trunk': 0.95,
    'primary': 0.85,
    'secondary': 0.70,
    'tertiary': 0.55,
    'residential': 0.25,
    'service': 0.15
}


def haversine_distance(lat1, lon1, lat2, lon2):
    """Great-circle distance in kilometers between two points."""
    R = 6371.0
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = (np.sin(dlat / 2.0) ** 2 + 
         np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * 
         np.sin(dlon / 2.0) ** 2)
    return 2.0 * R * np.arcsin(np.sqrt(a))


def extract_road_features(grid_gdf, roads_file):
    """
    Extract road activity features by intersecting OSM roads with H3 cells.
    
    Method:
    1. Project roads and grid to metric CRS (EPSG:3857)
    2. Intersect road geometries with H3 cell polygons
    3. For each segment, compute: length_meters × road_type_weight
    4. Sum per cell to get total weighted road activity
    5. Flag cells containing major roads (trunk/primary/motorway)
    """
    if not os.path.exists(roads_file):
        grid_gdf['road_activity'] = 0.0
        grid_gdf['major_road_access'] = 0
        grid_gdf['road_data_available'] = False
        return grid_gdf
    
    roads = gpd.read_file(roads_file)
    if roads.empty:
        grid_gdf['road_activity'] = 0.0
        grid_gdf['major_road_access'] = 0
        grid_gdf['road_data_available'] = False
        return grid_gdf
        
    grid_gdf['road_data_available'] = True
    roads_metric = roads.to_crs(epsg=3857)
    grid_metric = grid_gdf[['h3_index', 'geometry']].to_crs(epsg=3857)
    
    # Spatial intersection: clip roads to cell boundaries
    road_segments = gpd.overlay(
        roads_metric[['highway', 'geometry']], 
        grid_metric, 
        how='intersection'
    )
    road_segments['segment_len_m'] = road_segments.geometry.length
    
    def _get_road_weight(hw):
        if isinstance(hw, list):
            hw = hw[0] if len(hw) > 0 else 'residential'
        return ROAD_WEIGHTS.get(str(hw), 0.20)
    
    road_segments['weight'] = road_segments['highway'].apply(_get_road_weight)
    road_segments['weighted_activity'] = road_segments['segment_len_m'] * road_segments['weight']
    road_segments['is_major'] = road_segments['highway'].apply(
        lambda x: 1 if (isinstance(x, str) and x in ['trunk', 'primary', 'motorway']) or
                      (isinstance(x, list) and any(item in ['trunk', 'primary', 'motorway'] for item in x)) else 0
    )
    
    road_agg = road_segments.groupby('h3_index').agg(
        road_activity=('weighted_activity', 'sum'),
        major_road_access=('is_major', 'max')
    ).reset_index()
    
    grid_gdf = grid_gdf.merge(road_agg, on='h3_index', how='left')
    grid_gdf['road_activity'] = grid_gdf['road_activity'].fillna(0.0)
    grid_gdf['major_road_access'] = grid_gdf['major_road_access'].fillna(0).astype(int)
    
    return grid_gdf


def extract_poi_features(grid_gdf, pois_file):
    """
    Extract POI features by spatial joining OSM POIs with H3 cells.
    
    Method:
    1. Load POIs and classify into commercial / dwell / parking
    2. Spatial join POIs into H3 cells (point-in-polygon)
    3. Count POIs per category per cell
    """
    if not os.path.exists(pois_file):
        grid_gdf['commercial_poi_count'] = 0
        grid_gdf['dwell_poi_count'] = 0
        grid_gdf['parking_poi_count'] = 0
        grid_gdf['poi_data_available'] = False
        return grid_gdf
    
    pois = gpd.read_file(pois_file)
    if pois.empty:
        grid_gdf['commercial_poi_count'] = 0
        grid_gdf['dwell_poi_count'] = 0
        grid_gdf['parking_poi_count'] = 0
        grid_gdf['poi_data_available'] = False
        return grid_gdf
        
    grid_gdf['poi_data_available'] = True
    if pois.crs is None:
        pois.set_crs(epsg=4326, inplace=True)
    
    # Ensure point geometries
    pois_metric = pois.to_crs(epsg=3857)
    pois_metric['geometry'] = pois_metric.geometry.centroid
    pois_pts = pois_metric.to_crs(epsg=4326)
    
    # Classify POIs
    comm_shops = ['mall', 'supermarket', 'department_store']
    comm_amenities = ['marketplace', 'bank']
    dwell_amenities = ['restaurant', 'cafe', 'fast_food', 'cinema', 'hospital']
    dwell_tourism = ['hotel', 'attraction']
    
    pois_pts['is_commercial'] = pois_pts.apply(
        lambda r: 1 if (pd.notna(r.get('shop')) and r.get('shop') in comm_shops) or
                      (pd.notna(r.get('amenity')) and r.get('amenity') in comm_amenities) or
                      (pd.notna(r.get('office'))) else 0, axis=1
    )
    pois_pts['is_dwell'] = pois_pts.apply(
        lambda r: 1 if (pd.notna(r.get('amenity')) and r.get('amenity') in dwell_amenities) or
                      (pd.notna(r.get('tourism')) and r.get('tourism') in dwell_tourism) else 0, axis=1
    )
    pois_pts['is_parking'] = pois_pts.apply(
        lambda r: 1 if (pd.notna(r.get('amenity')) and r.get('amenity') in ['parking', 'parking_space']) else 0, axis=1
    )
    
    # Spatial join: which POIs fall in which cells
    pois_joined = gpd.sjoin(
        pois_pts[['is_commercial', 'is_dwell', 'is_parking', 'geometry']],
        grid_gdf[['h3_index', 'geometry']],
        how='inner',
        predicate='within'
    )
    
    poi_agg = pois_joined.groupby('h3_index').agg(
        commercial_poi_count=('is_commercial', 'sum'),
        dwell_poi_count=('is_dwell', 'sum'),
        parking_poi_count=('is_parking', 'sum')
    ).reset_index()
    
    import h3
    
    grid_gdf = grid_gdf.merge(poi_agg, on='h3_index', how='left')
    grid_gdf['commercial_poi_count'] = grid_gdf['commercial_poi_count'].fillna(0).astype(int)
    grid_gdf['dwell_poi_count'] = grid_gdf['dwell_poi_count'].fillna(0).astype(int)
    grid_gdf['parking_poi_count'] = grid_gdf['parking_poi_count'].fillna(0).astype(int)
    
    # ── NEIGHBOURHOOD AGGREGATION ──
    # A charger serves the immediate area, not just an exact H3 cell.
    grid_gdf.set_index('h3_index', inplace=True)
    
    comm_dict = grid_gdf['commercial_poi_count'].to_dict()
    dwell_dict = grid_gdf['dwell_poi_count'].to_dict()
    park_dict = grid_gdf['parking_poi_count'].to_dict()
    
    comm_neigh = []
    dwell_neigh = []
    park_neigh = []
    
    for h in grid_gdf.index:
        try:
            # h3-py compatibility
            if hasattr(h3, 'k_ring'):
                neighbors = h3.k_ring(h, 1)
            else:
                neighbors = h3.grid_disk(h, 1)
        except Exception:
            neighbors = [h]
            
        comm_neigh.append(sum(comm_dict.get(n, 0) for n in neighbors))
        dwell_neigh.append(sum(dwell_dict.get(n, 0) for n in neighbors))
        park_neigh.append(sum(park_dict.get(n, 0) for n in neighbors))
        
    grid_gdf['commercial_poi_count'] = comm_neigh
    grid_gdf['dwell_poi_count'] = dwell_neigh
    grid_gdf['parking_poi_count'] = park_neigh
    
    grid_gdf.reset_index(inplace=True)
    
    return grid_gdf


def extract_charger_features(grid_gdf, chargers):
    """
    Compute charger proximity features for each H3 cell.
    
    Method:
    1. For each cell centroid, compute haversine distance to ALL known chargers
    2. Record: nearest charger distance (km), name, operator
    3. Count chargers within 2.0 km radius
    
    If no charger data is available, sets default values and flags limitation.
    """
    if not chargers:
        grid_gdf['nearest_charger_km'] = 99.0
        grid_gdf['nearby_charger_count'] = 0
        grid_gdf['nearest_charger_name'] = 'No data'
        grid_gdf['nearest_charger_operator'] = 'No data'
        grid_gdf['charger_data_available'] = False
        return grid_gdf
    
    c_lats = np.array([float(c['lat']) for c in chargers])
    c_lons = np.array([float(c['lon']) for c in chargers])
    
    nearest_dist = []
    nearby_cnt = []
    nearest_name = []
    nearest_op = []
    
    for _, row in grid_gdf.iterrows():
        dists = haversine_distance(row['centroid_lat'], row['centroid_lon'], c_lats, c_lons)
        min_idx = np.argmin(dists)
        nearest_dist.append(round(float(dists[min_idx]), 2))
        nearby_cnt.append(int(np.sum(dists <= 2.0)))
        nearest_name.append(chargers[min_idx].get('name', 'Reference Station'))
        nearest_op.append(chargers[min_idx].get('operator', 'Public Operator'))
    
    grid_gdf['nearest_charger_km'] = nearest_dist
    grid_gdf['nearby_charger_count'] = nearby_cnt
    grid_gdf['nearest_charger_name'] = nearest_name
    grid_gdf['nearest_charger_operator'] = nearest_op
    grid_gdf['charger_data_available'] = True
    
    return grid_gdf
