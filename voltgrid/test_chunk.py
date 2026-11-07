import osmnx as ox
import geopandas as gpd
from shapely.geometry import box

ox.settings.max_query_area_size = 1000000 # 1 sq km
ox.settings.timeout = 180

b = box(77.1, 28.5, 77.3, 28.7) # Approx 20km x 20km = 400 sq km
print("Area:", b.area * 111111 * 111111 * 0.8) # rough sq meters
try:
    f = ox.features_from_polygon(b, tags={'amenity': 'charging_station'})
    print("Fetched", len(f))
except Exception as e:
    print("Error:", e)
