"""
bias_correction

A package for implementing the Olofsson et al. (2014) methodology for bias-adjusted
area estimation using stratified sampling. Specifically designed for cropland
extent analysis across the North American Central Flyway region.

Main Features:
- Bias correction for cropland area estimates
- Error rate calculation from stratified sampling
- Regional (Great Plains/Southern) and temporal processing
- Uncertainty estimation for adjusted areas
"""

import pandas as pd
import numpy as np
from typing import Dict,List


from bias_correction.adjustment import (
    cropland_area_adjustment,
    process_footprint,
    process_subregion,
    process_years
)

from bias_correction.config import (
    DATA_DIR,
    INPUT_DATA_DIR,
    FIG_DATA_DIR,
    YEARS,
    GP_STRATA_PROPORTIONS,
    MX_STRATA_PROPORTIONS,
    GP_OVERLAP_AREAS,
    MX_OVERLAP_AREAS,
    load_results,
    validate_input_data
)


from bias_correction.visualization import (
    create_multipanel_plot
)



__author__ = "Sean Carter"
__email__ = "sean.carter@umt.edu"

# Define what gets imported with "from bias_correction import *"
__all__ = [
    # Original adjustment functions
    'cropland_area_adjustment',
    'process_footprint',
    'process_subregion',
    'process_years',
    
    # Original configuration constants
    'GP_STRATA_PROPORTIONS',
    'MX_STRATA_PROPORTIONS',
    'GP_OVERLAP_AREAS',
    'MX_OVERLAP_AREAS',
    'YEARS',
    'validate_input_data',
    
    # Visualization functions and constants
    'DATA_DIR',
    'INPUT_DATA_DIR',
    'FIG_DATA_DIR',
    'load_results',
    'create_multipanel_plot'
]