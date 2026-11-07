import geopandas as gpd
from shapely.geometry import box
import osmnx as ox
import warnings
import urllib3
from src.osm_fetcher import _fetch_tiled

warnings.filterwarnings('ignore', category=urllib3.exceptions.InsecureRequestWarning)
ox.settings.timeout = 180
ox.settings.requests_kwargs = {'verify': False}
ox.settings.http_headers = {'User-Agent': 'VoltGrid-App/1.0 (Research)'}

# Mumbai roughly 19.0 to 19.2, 72.8 to 73.0 (small test box)
b = box(72.8, 19.0, 72.9, 19.1)

print("Starting fetch...")
tags = {'amenity': 'charging_station'}
gdf = _fetch_tiled(b, tags=tags, step_degrees=0.05)
print(f"Total deduplicated chargers: {len(gdf)}")
