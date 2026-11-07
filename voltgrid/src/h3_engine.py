"""
VoltGrid — H3 Engine
Generates Uber H3 hexagonal spatial grids for any city boundary.
Resolution 9 ≈ 0.1 km² cells, Resolution 8 ≈ 0.7 km² cells.
"""
import json
import os
import numpy as np
import geopandas as gpd
from shapely.geometry import Polygon, shape
import h3


def generate_h3_cells(boundary_geojson, resolution=9):
    """
    Generate H3 hexagonal cells for any city boundary.
    
    Parameters:
        boundary_geojson: dict — GeoJSON FeatureCollection with city boundary
        resolution: int — H3 resolution (8 or 9)
    
    Returns:
        GeoDataFrame with h3_index, geometry, centroid_lat, centroid_lon
    
    How it works:
    ─────────────────────────────────────────────────────
    1. Extract the polygon geometry from the boundary GeoJSON
    2. Convert polygon coordinates to H3's LatLngPoly format
    3. Use h3.polygon_to_cells() to fill the polygon with hexagons
    4. For each hex cell, compute its boundary polygon and centroid
    5. Return as a GeoDataFrame ready for spatial joins
    ─────────────────────────────────────────────────────
    """
    # Extract polygon from GeoJSON
    features = boundary_geojson.get('features', [])
    if not features:
        raise ValueError("Boundary GeoJSON has no features")
    
    poly_geom = shape(features[0]['geometry'])
    
    # Handle MultiPolygon — use the largest polygon
    if poly_geom.geom_type == 'MultiPolygon':
        poly_geom = max(poly_geom.geoms, key=lambda p: p.area)
    
    # H3 LatLngPoly expects (lat, lon) ordering
    coords = [(lat, lon) for lon, lat in poly_geom.exterior.coords]
    
    try:
        poly_h3 = h3.LatLngPoly(coords)
        cells = list(h3.polygon_to_cells(poly_h3, resolution))
    except AttributeError:
        # Fallback for older h3 versions
        geo_json_polygon = {
            'type': 'Polygon',
            'coordinates': [list(poly_geom.exterior.coords)]
        }
        cells = list(h3.polyfill(geo_json_polygon, resolution, geo_json_conformant=True))
    
    hex_records = []
    for cell in cells:
        try:
            boundary_latlng = h3.cell_to_boundary(cell)
            boundary = [(lon, lat) for lat, lon in boundary_latlng]
            lat, lon = h3.cell_to_latlng(cell)
        except AttributeError:
            boundary = h3.h3_to_geo_boundary(cell, geo_json=True)
            lat, lon = h3.h3_to_geo(cell)
        
        hex_records.append({
            'h3_index': cell,
            'geometry': Polygon(boundary),
            'centroid_lat': lat,
            'centroid_lon': lon
        })
    
    gdf = gpd.GeoDataFrame(hex_records, geometry='geometry', crs='EPSG:4326')
    return gdf


def estimate_cell_count(boundary_geojson, resolution=9):
    """Quick estimate of how many H3 cells a boundary would produce."""
    features = boundary_geojson.get('features', [])
    if not features:
        return 0
    poly_geom = shape(features[0]['geometry'])
    
    # Approximate area in km² (rough conversion from degrees)
    area_deg2 = poly_geom.area
    area_km2 = area_deg2 * 111 * 111  # rough at Indian latitudes
    
    # H3 res 9 ≈ 0.1 km² per cell, res 8 ≈ 0.7 km² per cell
    cell_area = 0.1 if resolution == 9 else 0.7
    return int(area_km2 / cell_area)
