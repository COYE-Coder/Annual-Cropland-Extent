import json
import os
import pandas as pd

# Get the root directory of the validation package
PACKAGE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Define the default relative path to the GeoJSON file
DEFAULT_GEOJSON_FILE = os.path.join(PACKAGE_ROOT, 'data', 'ag_validation_stratifiedSamples_full_coverage_geo.geojson')

# Define default output directory relative to package root - can be changed while running chip_pipeline.py
OUTPUT_DIR = os.path.join(PACKAGE_ROOT, "output", "validation_pipeline", "chips")



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
        geojson_file = DEFAULT_GEOJSON_FILE

    abs_geojson_file = os.path.abspath(geojson_file)

    try:
        with open(abs_geojson_file, 'r') as f:
            geojson = json.load(f)
        
        return {
            int(feature['id']): feature['geometry']['coordinates'] 
            for feature in geojson['features']
        }
    except FileNotFoundError:
        print(f"GeoJSON file not found: {abs_geojson_file}")
        return {}
    except json.JSONDecodeError:
        print(f"Error decoding GeoJSON file: {abs_geojson_file}")
        return {}

def load_geolookup_list(geojson_file: str = None) -> list:
    """
    Loads the GeoJSON file and creates a filtered list of tuples with coordinates, categories, and IDs.
    Filters to include only:
    1. Entries with combined_categories >= 100
    2. Up to 5000 entries per first digit category
    
    Args:
        geojson_file (str): Optional. The path to the GeoJSON file. If not provided, the default path will be used.
    
    Returns:
        A filtered list of tuples with structure: [(coordinates, combined_categories, id), ...]
    """
    if geojson_file is None:
        geojson_file = DEFAULT_GEOJSON_FILE

    abs_geojson_file = os.path.abspath(geojson_file)

    try:
        with open(abs_geojson_file, 'r') as f:
            geojson = json.load(f)
        
        # Convert to DataFrame for easier filtering
        df = pd.DataFrame([
            {'id': feature['id'], 
             'coordinates': feature['geometry']['coordinates'],
             'combined_categories': feature['properties']['combined_categories']} 
            for feature in geojson['features']
        ])
        
        # Filter for combined_categories >= 100
        df_100 = df[df['combined_categories'] >= 100]
        
        # Add first digit category and group
        df_100['first_digit_category'] = df_100['combined_categories'].apply(lambda x: str(x)[0])
        selected_entries = df_100.groupby('first_digit_category').head(5000)
        
        # Convert back to tuples list
        return [(row['coordinates'], row['combined_categories'], str(row['id'])) 
                for _, row in selected_entries.iterrows()]
        
    except FileNotFoundError:
        print(f"GeoJSON file not found: {abs_geojson_file}")
        return []
    except json.JSONDecodeError:
        print(f"Error decoding GeoJSON file: {abs_geojson_file}")
        return []


# Load the geo_lookup dictionary using the default relative path
geo_lookup = load_geo_lookup()
geolookup_list = load_geolookup_list()
