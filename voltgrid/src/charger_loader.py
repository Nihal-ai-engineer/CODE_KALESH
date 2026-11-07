"""
VoltGrid — Charger Loader
Loads real EV charger data for any city.
Sources: curated datasets, OpenChargeMap.
Never fabricates charger locations.
"""
import json
import os
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import requests
import time
from datetime import datetime


def load_chargers_for_city(city_slug):
    """
    Load real EV charger data for a specific city.
    Returns (list_of_charger_dicts, data_available_bool).
    
    If no charger data exists for the city, returns ([], False).
    NEVER fabricates charger coordinates.
    """
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data', city_slug)
    chargers_file = os.path.join(data_dir, 'chargers.json')
    
    if not os.path.exists(chargers_file):
        # Fallback to live OpenStreetMap query
        success = fetch_live_chargers_osm(city_slug, data_dir)
        if not success:
            return [], False
    
    with open(chargers_file, 'r', encoding='utf-8') as f:
        chargers = json.load(f)
    
    cleaned = []
    for c in chargers:
        lat = c.get('lat') or c.get('latitude')
        lon = c.get('lon') or c.get('longitude')
        if lat is None or lon is None:
            continue
        cleaned.append({
            'id': c.get('id', f"ref_{len(cleaned)+1}"),
            'name': c.get('name', 'Reference Charger'),
            'lat': float(lat),
            'lon': float(lon),
            'operator': c.get('operator', 'Public Operator'),
            'area_type': c.get('area_type', 'Urban Node'),
            'source': c.get('source', 'Curated Reference Dataset'),
            'verification_status': c.get('verification_status', 'Curated Reference'),
            'retrieved_at': c.get('retrieved_at', 'Unknown')
        })
    
    return cleaned, len(cleaned) > 0


def fetch_live_chargers_osm(city_slug, data_dir):
    """
    Fetch live EV charging stations from OpenStreetMap using osmnx.
    Requires no API key and provides excellent coverage for Indian cities.
    """
    import osmnx as ox
    import urllib3
    import warnings
    try:
        warnings.filterwarnings('ignore', category=urllib3.exceptions.InsecureRequestWarning)
        ox.settings.timeout = 60
        ox.settings.requests_kwargs = {'verify': False}
        ox.settings.http_headers = {'User-Agent': 'VoltGrid-App/1.0 (Research)'}
        
        from src.city_resolver import get_city_data_dir
        import geopandas as gpd
        import os
        
        boundary_file = os.path.join(get_city_data_dir(city_slug), 'boundary.geojson')
        if not os.path.exists(boundary_file):
            return False
            
        boundary = gpd.read_file(boundary_file)
        if boundary.empty:
            return False
            
        polygon = boundary.geometry.iloc[0]
        tags = {'amenity': 'charging_station'}
        
        from src.osm_fetcher import _fetch_tiled
        chargers_gdf = _fetch_tiled(polygon, tags=tags)
        
        if chargers_gdf.empty:
            return False
            
        chargers_list = []
        if chargers_gdf.crs is None:
            chargers_gdf.set_crs(epsg=4326, inplace=True)
            
        chargers_gdf['geometry'] = chargers_gdf.geometry.centroid
        
        for idx, row in chargers_gdf.iterrows():
            chargers_list.append({
                "id": str(idx),
                "name": row.get('name', 'Public EV Charger'),
                "lat": row.geometry.y,
                "lon": row.geometry.x,
                "operator": row.get('operator', 'Unknown Operator'),
                "source": "OpenStreetMap",
                "retrieved_at": time.strftime('%Y-%m-%d %H:%M:%S')
            })
            
        os.makedirs(data_dir, exist_ok=True)
        with open(os.path.join(data_dir, 'chargers.json'), 'w', encoding='utf-8') as f:
            json.dump(chargers_list, f, indent=2)
            
        return True
    except Exception as e:
        print(f"Warning: Failed to fetch live OSM chargers: {e}")
        return False


def get_chargers_gdf(city_slug):
    """Returns a GeoDataFrame of chargers for the city."""
    chargers, available = load_chargers_for_city(city_slug)
    if not chargers:
        return gpd.GeoDataFrame(
            columns=['id', 'name', 'operator', 'geometry'],
            geometry='geometry', crs='EPSG:4326'
        ), False
    
    df = pd.DataFrame(chargers)
    geometry = [Point(xy) for xy in zip(df['lon'], df['lat'])]
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs='EPSG:4326')
    return gdf, True
