"""
VoltGrid — City Resolver
Resolves city names to boundaries, slugs, and metadata.
Uses cached data for offline-ready cities, OSMnx for live resolution.
"""
import os
import json
import re
import geopandas as gpd

BASE_DIR = os.path.join(os.path.dirname(__file__), '..')
DATA_DIR = os.path.join(BASE_DIR, 'data')
CITY_INDEX_FILE = os.path.join(DATA_DIR, 'india', 'city_index.json')

# Maximum area (km²) for H3 res 9 — above this, use res 8 first pass
MAX_AREA_RES9_KM2 = 250


def load_city_index():
    """Load the national city registry."""
    if not os.path.exists(CITY_INDEX_FILE):
        return []
    with open(CITY_INDEX_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get('cities', [])


def slugify(name):
    """Convert city name to filesystem-safe slug."""
    slug = name.lower().strip()
    slug = re.sub(r'[^a-z0-9]+', '_', slug)
    slug = slug.strip('_')
    return slug


def find_city_in_index(query):
    """Search the city index for a matching city."""
    cities = load_city_index()
    query_lower = query.lower().strip()
    
    # Exact slug match
    for c in cities:
        if c['slug'] == query_lower or c['name'].lower() == query_lower:
            return c
    
    # Partial match
    for c in cities:
        if query_lower in c['name'].lower() or query_lower in c['slug']:
            return c
    
    return None


def get_city_data_dir(city_slug):
    """Get the data directory path for a city."""
    return os.path.join(DATA_DIR, city_slug)


def is_city_cached(city_slug):
    """Check if a city has cached analysis data."""
    city_dir = get_city_data_dir(city_slug)
    metadata_file = os.path.join(city_dir, 'metadata.json')
    boundary_file = os.path.join(city_dir, 'boundary.geojson')
    return os.path.exists(metadata_file) and os.path.exists(boundary_file)


def has_analysis_cache(city_slug):
    """Check if a city has pre-computed analysis results."""
    city_dir = get_city_data_dir(city_slug)
    return os.path.exists(os.path.join(city_dir, 'analysis_cache.json'))


def load_city_metadata(city_slug):
    """Load metadata.json for a cached city."""
    meta_file = os.path.join(get_city_data_dir(city_slug), 'metadata.json')
    if os.path.exists(meta_file):
        with open(meta_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def load_city_boundary(city_slug):
    """Load the cached boundary GeoJSON for a city."""
    boundary_file = os.path.join(get_city_data_dir(city_slug), 'boundary.geojson')
    if os.path.exists(boundary_file):
        with open(boundary_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def resolve_city_boundary_live(city_name):
    """
    Resolve a city boundary from OpenStreetMap using OSMnx.
    
    Strategy:
    1. Try geocode_to_gdf (returns admin boundary polygon)
    2. If that fails (small towns), geocode to a point and create a 3 km buffer
    
    Returns: GeoDataFrame with boundary polygon
    """
    import osmnx as ox
    from shapely.geometry import Point
    import geopandas as _gpd
    import warnings
    import urllib3
    warnings.filterwarnings('ignore', category=urllib3.exceptions.InsecureRequestWarning)

    ox.settings.timeout = 180
    ox.settings.requests_kwargs = {'verify': False}
    ox.settings.http_headers = {'User-Agent': 'VoltGrid-App/1.0 (Research)'}
    # Removed Kumi systems override to use default overpass API (more stable)

    # Normalize: don't double-append ", India"
    query = city_name.strip()
    if not query.lower().endswith('india'):
        query = f"{query}, India"

    # Attempt 1: Admin boundary polygon
    try:
        gdf = ox.geocode_to_gdf(query)
        if not gdf.empty:
            return gdf
    except Exception:
        pass

    # Attempt 2: Geocode to point + 3 km buffer (works for small towns)
    try:
        lat, lon = ox.geocode(query)
        point = Point(lon, lat)
        # 3 km buffer (≈ 0.027 degrees at Indian latitudes)
        buffer_deg = 0.027
        buffered = point.buffer(buffer_deg)
        gdf = _gpd.GeoDataFrame(
            [{'name': city_name, 'geometry': buffered}],
            geometry='geometry', crs='EPSG:4326'
        )
        return gdf
    except Exception:
        pass

    raise RuntimeError(
        f"Could not resolve '{city_name}' via OpenStreetMap. "
        f"Check spelling or try a nearby larger city."
    )


def get_h3_resolution_for_city(area_km2):
    """
    Determine H3 resolution based on city area.
    Small cities (< 250 km²): resolution 9 (~0.1 km² cells)
    Large cities (>= 250 km²): resolution 8 (~0.7 km² cells) for first pass
    """
    if area_km2 < MAX_AREA_RES9_KM2:
        return 9
    else:
        return 8


def get_all_cached_cities():
    """Return a list of all cities that have cached data."""
    cached = []
    if not os.path.exists(DATA_DIR):
        return cached
    
    for item in os.listdir(DATA_DIR):
        item_path = os.path.join(DATA_DIR, item)
        if os.path.isdir(item_path) and item != 'india':
            meta = load_city_metadata(item)
            if meta:
                cached.append({
                    'slug': item,
                    'name': meta.get('city', item.replace('_', ' ').title()),
                    'state': meta.get('state', ''),
                    'charger_count': meta.get('charger_count', 0),
                    'offline_ready': meta.get('offline_ready', False),
                    'generated_at': meta.get('generated_at', 'Unknown'),
                    'h3_resolution': meta.get('h3_resolution', 9),
                    'study_area_km2': meta.get('study_area_km2', 0),
                })
    return cached
