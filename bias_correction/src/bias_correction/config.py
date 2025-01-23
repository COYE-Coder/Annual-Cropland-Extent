# src/bias_correction/config.py

"""
Configuration settings for cropland bias correction.

This module contains the constants and parameters needed for the bias
correction workflow, including strata proportions, overlap areas, and
year ranges.


"""
import json
import numpy as np
from typing import Dict, List, Union
import pandas as pd
from pathlib import Path

# Package root directory and data paths
PACKAGE_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PACKAGE_ROOT / 'data'
INPUT_DATA_DIR = DATA_DIR / 'input'
FIG_DATA_DIR = DATA_DIR / 'misc_fig_data'

def validate_paths():
    """Validate that all required data files exist."""
    required_files = [
        INPUT_DATA_DIR / 'cropscope_gross.csv',
        INPUT_DATA_DIR / 'cropscope_net.csv',
        INPUT_DATA_DIR / 'great_plains_accuracy_points_gdrive.csv',
        INPUT_DATA_DIR / 'mexico_accuracy_points_gdrive.csv',
        INPUT_DATA_DIR / 'corrected_cropland_area_estimates.json',
        FIG_DATA_DIR / 'canada_transparent.png',
        FIG_DATA_DIR / 'mexico_transparent.png',
        FIG_DATA_DIR / 'united_states_transparent.png',
        FIG_DATA_DIR / 'total_transparent.png'
    ]
    
    missing_files = [f for f in required_files if not f.exists()]
    if missing_files:
        raise FileNotFoundError(f"Missing required files: {missing_files}")

# Call validation when module is imported
validate_paths()


# Analysis time period
YEARS = range(1996, 2022)

# Regional strata proportions
# Represents the relative size of each stratum in the sampling design
# Great Plains strata proportions
GP_STRATA_PROPORTIONS = {
    1: 0.3399459905021893,    # likely stable croplands
    2: 0.04854199924345394,   # cropland gain
    3: 0.055592609114006625,  # cropland loss
    4: 0.5540253044095518, # likely stable non-croplands
    5: 0.0018940967307983225  # possible errors
}

# Mexico strata proportions
MX_STRATA_PROPORTIONS = {
    1: 0.03336170578959062,   # likely stable croplands
    2: 0.008431742977548621,  # cropland gain
    3: 0.001045225520779897,  # cropland loss
    4: 0.9321715151583109, # Likely stable non-croplands
    5: 0.02498981055377003    # possible errors
}

# Regional overlap areas (in million acres)
MX_OVERLAP_AREAS: Dict[str, float] = {
    'total': 195.50,
    'us': 54.00,
    'mx': 141.51,
    'canada': 0
}

GP_OVERLAP_AREAS: Dict[str, float] = {
    'us': 550.7870614297041,
    'canada': 113.59558968030782,
    'mx': 25.740657567547277,
    'total': 690.1233086775592
}

# Required columns for validation data
REQUIRED_COLUMNS: List[str] = [
    'strata',
    'landcover_code',
    'window_ag',
    'year'
]

# Country-specific area columns
COUNTRY_COLUMNS: List[str] = [
    'us_mill_acres',
    'canada_mill_acres',
    'mx_mill_acres',
    'total_mill_acres'
]

# Input data file paths
DATA_FILES: Dict[str, str] = {
    'gross_cropland': str(INPUT_DATA_DIR / 'cropscope_gross.csv'),
    'net_cropland': str(INPUT_DATA_DIR / 'cropscope_net.csv'),
    'gp_accuracy': str(INPUT_DATA_DIR / 'great_plains_accuracy_points_gdrive.csv'),
    'mx_accuracy': str(INPUT_DATA_DIR / 'mexico_accuracy_points_gdrive.csv')
}

def validate_input_data(df: pd.DataFrame, required_cols: List[str] = REQUIRED_COLUMNS) -> bool:
    """
    Validate that input dataframe contains required columns.
    
    Args:
        df: Input DataFrame to validate
        required_cols: List of required column names
        
    Returns:
        bool: True if all required columns present
        
    Raises:
        ValueError: If missing required columns
    """
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")
    return True

def convert_dict_to_df(data):
    """Convert the JSON-serialized format back to DataFrame"""
    if isinstance(data, dict):
        if 'columns' in data and 'data' in data:
            return pd.DataFrame(data['data'], columns=data['columns'])
        return {k: convert_dict_to_df(v) for k, v in data.items()}
    return data

def load_results(filepath: str) -> Dict:
    """
    Load saved results from JSON file.
    
    Args:
        filepath: Path to JSON results file
    
    Returns:
        Dict: Reconstructed results dictionary
    """
    with open(filepath, 'r') as f:
        loaded_data = json.load(f)
        return convert_dict_to_df(loaded_data)