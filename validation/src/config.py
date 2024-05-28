import json
import os

# Define the default relative path to the GeoJSON file
DEFAULT_GEOJSON_FILE = 'data/ag_validation_stratifiedSamples_full_coverage_geo.geojson'

def load_geo_lookup(geojson_file: str = None) -> dict:
    """
    Loads the GeoJSON file and creates a lookup dictionary mapping IDs to coordinates.

    Args:
        geojson_file (str): Optional. The path to the GeoJSON file. If not provided, the default path will be used.

    Returns:
        A dictionary with the following structure:
        {
            id (int): [longitude (float), latitude (float)]
        }
    """
    if geojson_file is None:
        # Use the default relative path if geojson_file is not provided
        geojson_file = DEFAULT_GEOJSON_FILE

    # Get the absolute path to the GeoJSON file
    abs_geojson_file = os.path.abspath(geojson_file)

    try:
        with open(abs_geojson_file, 'r') as f:
            geojson = json.load(f)
        
        items = [
            (x['geometry']['coordinates'], x['properties']['combined_categories'], x['id'])
            for x in geojson['features']
        ]

        return {int(item[2]): item[0] for item in items}
    except FileNotFoundError:
        print(f"GeoJSON file not found: {abs_geojson_file}")
        return {}
    except json.JSONDecodeError:
        print(f"Error decoding GeoJSON file: {abs_geojson_file}")
        return {}

# Load the geo_lookup dictionary using the default relative path
geo_lookup = load_geo_lookup()
geo_lookup: dict = load_geo_lookup()
