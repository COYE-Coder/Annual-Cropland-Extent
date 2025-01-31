import ee
import sys

def initialize_earth_engine():
    """Initialize Earth Engine authentication."""
    try:
        ee.Initialize()
    except Exception as e:
        print("Earth Engine authentication required.")
        print("Please run 'earthengine authenticate' in your terminal first.")
        print("Error:", str(e))
        sys.exit(1)

