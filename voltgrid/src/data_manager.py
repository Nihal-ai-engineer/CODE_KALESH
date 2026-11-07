"""
VoltGrid — Data Manager
Manages the complete city analysis pipeline.
One function: analyze_city() — works identically for any Indian city.
"""
import os
import json
import time
import geopandas as gpd

from src.city_resolver import (
    get_city_data_dir, is_city_cached, load_city_boundary,
    load_city_metadata, get_h3_resolution_for_city, find_city_in_index
)
from src.h3_engine import generate_h3_cells
from src.feature_engine import (
    extract_road_features, extract_poi_features, extract_charger_features
)
from src.charger_loader import load_chargers_for_city
from src.scoring import compute_scores, select_top_candidates


def analyze_city(city_slug, progress_callback=None):
    """
    Run the complete analysis pipeline for a city.
    Same code for Chandigarh, Delhi, Bengaluru, or any other city.
    
    Pipeline:
    ─────────────────────────────────────────────
    1. Load boundary (cached or live)
    2. Load roads (cached OSM data)
    3. Load POIs (cached OSM data)
    4. Load charger locations
    5. Generate H3 grid
    6. Extract road features
    7. Extract POI features
    8. Extract charger proximity features
    9. Compute MCDA scores
    10. Select top candidate zones
    11. Cache results
    ─────────────────────────────────────────────
    
    Returns:
        dict with 'scored_gdf', 'candidates', 'chargers', 
        'charger_data_available', 'metadata', 'city_name'
    """
    city_dir = get_city_data_dir(city_slug)
    
    def _progress(step, msg):
        if progress_callback:
            progress_callback(step, msg)
    
    # ── Step 1: Load boundary ──
    _progress(1, "Loading city boundary...")
    boundary = load_city_boundary(city_slug)
    if boundary is None:
        raise FileNotFoundError(f"No boundary data for '{city_slug}'. Generate analysis first.")
    
    metadata = load_city_metadata(city_slug) or {}
    city_name = metadata.get('city', city_slug.replace('_', ' ').title())
    area_km2 = metadata.get('study_area_km2', 100)
    
    # ── Step 2: Determine H3 resolution ──
    h3_res = get_h3_resolution_for_city(area_km2)
    _progress(2, f"Generating H3 grid (resolution {h3_res}, ~{'0.1' if h3_res == 9 else '0.7'} km² cells)...")
    
    # ── Step 3: Generate H3 cells ──
    grid_gdf = generate_h3_cells(boundary, resolution=h3_res)
    grid_gdf['city'] = city_name
    
    # ── Step 4: Extract road features ──
    _progress(3, "Aggregating road activity with weighted hierarchy...")
    roads_file = os.path.join(city_dir, 'roads.gpkg')
    grid_gdf = extract_road_features(grid_gdf, roads_file)
    
    # ── Step 5: Extract POI features ──
    _progress(4, "Mapping commercial & dwell opportunity POIs...")
    pois_file = os.path.join(city_dir, 'pois.gpkg')
    grid_gdf = extract_poi_features(grid_gdf, pois_file)
    
    # ── Step 6: Load chargers and extract proximity ──
    _progress(5, "Calculating charger coverage gaps...")
    chargers, charger_data_available = load_chargers_for_city(city_slug)
    grid_gdf = extract_charger_features(grid_gdf, chargers)
    
    # ── Step 7: Compute scores ──
    _progress(6, "Computing multi-criteria recommendation scores...")
    scored_gdf = compute_scores(grid_gdf)
    
    # ── Step 8: Select candidates ──
    _progress(7, "Selecting top candidate zones with spatial separation...")
    candidates = select_top_candidates(scored_gdf, top_n=3, exclusion_radius_km=1.5)
    
    # ── Step 9: Cache results ──
    _progress(8, "Caching analysis results...")
    _save_analysis_cache(city_slug, scored_gdf, candidates, metadata)
    
    return {
        'scored_gdf': scored_gdf,
        'candidates': candidates,
        'chargers': chargers,
        'charger_data_available': charger_data_available,
        'metadata': metadata,
        'city_name': city_name,
        'h3_resolution': h3_res,
        'cell_count': len(scored_gdf)
    }


def load_cached_analysis(city_slug):
    """Load previously cached analysis results."""
    city_dir = get_city_data_dir(city_slug)
    cache_file = os.path.join(city_dir, 'analysis_cache.json')
    
    if not os.path.exists(cache_file):
        return None
    
    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache = json.load(f)
        return cache
    except Exception:
        return None


def _save_analysis_cache(city_slug, scored_gdf, candidates, metadata):
    """Save analysis results to cache for fast reload."""
    city_dir = get_city_data_dir(city_slug)
    cache_file = os.path.join(city_dir, 'analysis_cache.json')
    
    try:
        cache = {
            'city_slug': city_slug,
            'cell_count': len(scored_gdf),
            'candidates': candidates,
            'generated_at': time.strftime('%Y-%m-%d %H:%M:%S'),
        }
        os.makedirs(city_dir, exist_ok=True)
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache, f, indent=2, default=str)
    except Exception as e:
        print(f"Warning: could not save analysis cache: {e}")


def generate_city_live(city_slug, display_name, osm_query, progress_callback=None):
    """
    Generate analysis for an uncached city using live OSM data.
    Requires internet connection.
    
    Pipeline:
    1. Resolve boundary from OSMnx
    2. Fetch roads from OSM
    3. Fetch POIs from OSM
    4. Save all data to city directory
    5. Run standard analysis pipeline
    """
    from src.city_resolver import resolve_city_boundary_live
    from src.osm_fetcher import fetch_roads_for_boundary, fetch_pois_for_boundary
    
    def _progress(step, msg):
        if progress_callback:
            progress_callback(step, msg)
    
    city_dir = get_city_data_dir(city_slug)
    os.makedirs(city_dir, exist_ok=True)
    
    # Step 1: Resolve boundary
    _progress(1, f"Resolving boundary for {display_name}...")
    boundary_gdf = resolve_city_boundary_live(osm_query)
    
    # Save boundary
    boundary_geojson = json.loads(boundary_gdf.to_json())
    boundary_file = os.path.join(city_dir, 'boundary.geojson')
    with open(boundary_file, 'w', encoding='utf-8') as f:
        json.dump(boundary_geojson, f)
    
    # Compute area using local UTM projection instead of Web Mercator
    utm_crs = boundary_gdf.estimate_utm_crs()
    area_km2 = float(boundary_gdf.to_crs(utm_crs).geometry.area.iloc[0] / 1e6)
    
    # Step 2: Fetch roads
    _progress(2, "Fetching road network from OpenStreetMap...")
    roads_file = os.path.join(city_dir, 'roads.gpkg')
    try:
        road_count = fetch_roads_for_boundary(boundary_gdf, roads_file)
    except Exception as e:
        road_count = 0
        print(f"Warning: Could not fetch roads: {e}")
    
    # Step 3: Fetch POIs
    import time
    time.sleep(3) # Avoid Overpass API connection refused
    _progress(3, "Fetching POIs from OpenStreetMap...")
    pois_file = os.path.join(city_dir, 'pois.gpkg')
    try:
        poi_count = fetch_pois_for_boundary(boundary_gdf, pois_file)
    except Exception as e:
        poi_count = 0
        print(f"Warning: Could not fetch POIs: {e}")
    
    # Step 4: Save metadata
    _progress(4, "Saving city metadata...")
    metadata = {
        "city": display_name,
        "city_slug": city_slug,
        "state": "",
        "display_name": display_name,
        "osm_query": osm_query,
        "generated_at": time.strftime('%Y-%m-%d %H:%M:%S'),
        "charger_source": "None — charger data not available for this city",
        "charger_count": 0,
        "h3_resolution": get_h3_resolution_for_city(area_km2),
        "data_completeness": {
            "boundary": True,
            "roads": road_count > 0,
            "pois": poi_count > 0,
            "chargers": False,
            "traffic": False,
            "grid_capacity": False,
            "land_price": False,
            "charger_utilization": False
        },
        "study_area_km2": round(area_km2, 1),
        "offline_ready": False
    }
    meta_file = os.path.join(city_dir, 'metadata.json')
    with open(meta_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)
    
    # Step 5: Run analysis
    _progress(5, "Running spatial analysis pipeline...")
    return analyze_city(city_slug, progress_callback=lambda s, m: _progress(5 + s, m))
