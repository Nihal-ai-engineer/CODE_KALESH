"""
VoltGrid — OSM Fetcher
Fetches real OpenStreetMap data (roads, POIs) for any city boundary.
Uses OSMnx for reliable data retrieval.
"""
import os
import geopandas as gpd
import time
import osmnx as ox

import numpy as np
from shapely.geometry import box
import pandas as pd

GLOBAL_ENDPOINTS = [
    'https://overpass-api.de/api',          # Default
    'https://lz4.overpass-api.de/api',      # High perf clone
    'https://overpass.kumi.systems/api',    # Reliable fallback
    'https://overpass.osm.ch/api'           # Swiss mirror
]

def _fetch_chunk_with_retries(polygon, tags, retries=3):
    """
    Robust wrapper for OSMnx that cycles through multiple Overpass API mirrors.
    Prevents 'Connection Refused' crashes during high load.
    """
    global GLOBAL_ENDPOINTS
    last_exception = None
    
    for attempt in range(retries):
        for idx, endpoint in enumerate(GLOBAL_ENDPOINTS):
            try:
                ox.settings.overpass_url = endpoint
                print(f"Trying Overpass mirror: {endpoint}...")
                
                # Fetch features
                gdf = ox.features_from_polygon(polygon, tags=tags)
                
                # If successful, bubble this endpoint to the front to save time on next chunks
                if idx > 0:
                    GLOBAL_ENDPOINTS.insert(0, GLOBAL_ENDPOINTS.pop(idx))
                    
                return gdf
                
            except Exception as e:
                last_exception = e
                print(f"Failed mirror {endpoint}: {e}")
                
        # If all endpoints failed on this attempt, wait and retry
        print(f"Attempt {attempt + 1}/{retries} failed on all mirrors. Backing off 5 seconds...")
        time.sleep(5)
        
    print(f"All retries failed for this chunk. Last exception: {last_exception}")
    return gpd.GeoDataFrame() # Return empty df on complete failure


def _fetch_tiled(polygon, tags, step_degrees=0.05):
    """
    Slices a large polygon into a grid (approx 5km x 5km) and fetches each tile
    independently. Merges and deduplicates the results at the end.
    """
    minx, miny, maxx, maxy = polygon.bounds
    x_coords = np.arange(minx, maxx + step_degrees, step_degrees)
    y_coords = np.arange(miny, maxy + step_degrees, step_degrees)
    
    tiles = []
    for i in range(len(x_coords) - 1):
        for j in range(len(y_coords) - 1):
            tile_box = box(x_coords[i], y_coords[j], x_coords[i+1], y_coords[j+1])
            if tile_box.intersects(polygon):
                intersection = tile_box.intersection(polygon)
                if intersection.geom_type in ['Polygon', 'MultiPolygon'] and intersection.area > 0:
                    tiles.append(intersection)
                    
    print(f"Spatially chunked bounding box into {len(tiles)} intersecting tiles.")
    
    results = []
    for idx, tile in enumerate(tiles):
        print(f"Fetching tile {idx+1}/{len(tiles)}...")
        gdf = _fetch_chunk_with_retries(tile, tags=tags)
        if not gdf.empty:
            results.append(gdf)
            
    if not results:
        return gpd.GeoDataFrame()
        
    merged = pd.concat(results)
    # Deduplicate based on OSM ID (which is in the index)
    merged = merged[~merged.index.duplicated(keep='first')]
    print(f"Merge complete. Fetched {len(merged)} total unique features.")
    return merged



def fetch_roads_for_boundary(boundary_gdf, output_path):
    """
    Fetch real road network from OpenStreetMap for a given boundary.
    Saves to GPKG format.
    
    Road types fetched: motorway, trunk, primary, secondary, tertiary, residential, service
    """
    import osmnx as ox
    import warnings
    import urllib3
    warnings.filterwarnings('ignore', category=urllib3.exceptions.InsecureRequestWarning)
    
    # Configure OSMnx to be more robust
    ox.settings.timeout = 60
    ox.settings.max_query_area_size = 50 * 1000 * 50 * 1000
    ox.settings.requests_kwargs = {'verify': False}
    ox.settings.http_headers = {'User-Agent': 'VoltGrid-App/1.0 (Research)'}
    # Use an alternative endpoint to avoid rate limits
    # ox.settings.overpass_endpoint = 'https://overpass.kumi.systems/api/interpreter'
    
    polygon = boundary_gdf.geometry.iloc[0]
    tags = {
        'highway': ['motorway', 'trunk', 'primary', 'secondary', 
                     'tertiary', 'residential', 'service']
    }
    
    try:
        roads = _fetch_tiled(polygon, tags=tags)
        
        if roads.empty:
            return 0
            
        roads = roads[roads.geometry.type.isin(['LineString', 'MultiLineString'])]
        
        # Convert list columns to string to avoid serialization errors
        for col in roads.columns:
            if col != 'geometry' and roads[col].apply(lambda x: isinstance(x, list)).any():
                roads[col] = roads[col].astype(str)
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        roads.to_file(output_path, driver='GPKG')
        return len(roads)
    except Exception as e:
        import traceback
        with open('debug_roads.txt', 'w') as f:
            f.write(traceback.format_exc())
        raise


def fetch_pois_for_boundary(boundary_gdf, output_path):
    """
    Fetch real Points of Interest from OpenStreetMap for a given boundary.
    
    Categories:
    - Commercial: mall, supermarket, department_store, marketplace, offices
    - Dwell: restaurant, cafe, fast_food, cinema, hotel, hospital
    - Parking: parking, parking_space
    """
    import osmnx as ox
    import warnings
    import urllib3
    warnings.filterwarnings('ignore', category=urllib3.exceptions.InsecureRequestWarning)
    
    # Configure OSMnx to be more robust
    ox.settings.timeout = 60
    ox.settings.max_query_area_size = 50 * 1000 * 50 * 1000
    ox.settings.requests_kwargs = {'verify': False}
    ox.settings.http_headers = {'User-Agent': 'VoltGrid-App/1.0 (Research)'}
    # Use an alternative endpoint to avoid rate limits
    # ox.settings.overpass_endpoint = 'https://overpass.kumi.systems/api/interpreter'
    
    polygon = boundary_gdf.geometry.iloc[0]
    tags = {
        'shop': ['mall', 'supermarket', 'department_store'],
        'amenity': ['marketplace', 'bank', 'restaurant', 'cafe', 'fast_food',
                     'cinema', 'hospital', 'parking', 'parking_space'],
        'office': True,
        'tourism': ['hotel']
    }
    
    pois = _fetch_tiled(polygon, tags=tags)
    
    if pois.empty:
        return 0
    
    # Convert mixed geometries to centroids
    pois['geometry'] = pois.geometry.centroid
    
    # Convert list columns to string
    for col in pois.columns:
        if col != 'geometry' and pois[col].apply(lambda x: isinstance(x, list)).any():
            pois[col] = pois[col].astype(str)
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    pois.to_file(output_path, driver='GPKG')
    return len(pois)
