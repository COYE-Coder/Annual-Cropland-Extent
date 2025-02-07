# src/bias_correction/adjustment.py

"""
Bias correction module for cropland area estimation.

This module implements the Olofsson et al. (2014) methodology for bias-adjusted
area estimation using stratified sampling. It processes both total (cumulative) and
active (annual) cropland footprints across the Great Plains and Southern Subregions
of North America. Each subregion is processed separately before combining cropland
area and error estimates into one single value. 

Area estimates are then provided across each political boundary (Canada, US, and Mexico).

The module supports:
- Error rate calculation from confusion matrices
- Area adjustment based on commission and omission errors
- Standard error estimation for adjusted areas
- Regional and temporal processing of cropland estimates
"""

import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix
from typing import Dict, List, Union, Optional

def calculate_se(strata_areas: np.ndarray, 
                n_h: np.ndarray, 
                N_h: float, 
                p_bar_h: np.ndarray) -> float:
    """
    Calculate standard error for stratified sampling following Olofsson et al. (2014).
    
    Args:
        strata_areas: Areas of each stratum (Ah in methods)
        n_h: Sample size in each stratum
        N_h: Total number of possible sampling units
        p_bar_h: Mean cropland proportion of samples in stratum h
    
    Returns:
        float: Standard error for the adjusted area estimate
    """
    s_squared_ph = p_bar_h * (1 - p_bar_h)  # Sample variance (Sph^2)
    return np.sqrt(np.sum((strata_areas**2 * (1 - n_h/N_h) * s_squared_ph) / n_h))

def calculate_error_rates(stratum_df: pd.DataFrame) -> tuple:
    """
    Calculate commission and omission error rates from confusion matrix.
    
    Uses visual interpretation samples (landcover_code) compared against
    model predictions (window_ag) to compute error rates.
    
    Args:
        stratum_df: DataFrame containing 'landcover_code' (reference) and 
                   'window_ag' (prediction) columns for a single stratum
    
    Returns:
        tuple: (commission_error_rate, omission_error_rate)
    """
    cm = confusion_matrix(stratum_df['landcover_code'], stratum_df['window_ag'], labels=[0,1])
    if cm.sum() > 0:
        tn, fp, fn, tp = cm.ravel()
        commission_error_rate = fp / (fp + tp) if (fp + tp) > 0 else 0
        omission_error_rate = fn / (fn + tp) if (fn + tp) > 0 else 0
    else:
        commission_error_rate = omission_error_rate = 0
    return commission_error_rate, omission_error_rate

def calculate_adjustments(strata_areas: np.ndarray, 
                        commission_rates: List[float], 
                        omission_rates: List[float],
                        strata_proportions: np.ndarray) -> np.ndarray:
    """
    Calculate area adjustments based on commission and omission errors.
    
    Implements the adjustment formula from Olofsson et al. (2014):
    Aadjusted = Aobserved + Σ(wh(Oh - Ch)Ah)
    
    Args:
        strata_areas: Area of each stratum (Ah)
        commission_rates: Commission error rates by stratum (Ch)
        omission_rates: Omission error rates by stratum (Oh)
        strata_proportions: Proportion of total area in each stratum (wh)
    
    Returns:
        np.ndarray: Adjustments for each stratum
    """
    adjustments = []
    for area, comm_rate, omis_rate in zip(strata_areas, commission_rates, omission_rates):
        commission_adjustment = area * comm_rate
        omission_adjustment = area * omis_rate
        net_adjustment = omission_adjustment - commission_adjustment
        adjustments.append(net_adjustment)
    return np.array(adjustments) * strata_proportions

def cropland_area_adjustment(observed_area: float,
                           accuracy_df: pd.DataFrame, 
                           strata_proportions: np.ndarray,
                           total_area: float) -> Dict[str, float]:
    """
    Calculate bias-adjusted cropland area estimates following Olofsson et al. (2014).

    Processes validation points within each stratum to compute error-adjusted area
    estimates and associated uncertainties for cropland extent.

    Args:
        observed_area: Original cropland area from model predictions
        accuracy_df: DataFrame containing validation points with columns:
                    'strata': Stratum ID (1-5)
                    'landcover_code': Reference classification (0/1)
                    'window_ag': Model prediction (0/1)
        strata_proportions: Relative size of each stratum (wh)
        total_area: Total area of the region in acres

    Returns:
        Dict containing:
            'observed': Original area estimate
            'adjusted': Bias-adjusted area estimate
            'adjustment': Net adjustment applied
            'se': Standard error of adjusted estimate
            'ci_95': 95% confidence interval
    """
    strata_areas = []
    commission_error_rates = []
    omission_error_rates = []
    n_h = []
    p_bar_h = []
    used_strata = []  # Keep track of which strata we actually use

    
    # Only process strata that exist in the proportions
    for stratum in sorted(strata_proportions.keys()):
        stratum_df = accuracy_df[accuracy_df['strata'] == stratum]
        
        if len(stratum_df) == 0:
            continue
            
        # Add the area for this stratum
        strata_areas.append(strata_proportions[stratum] * total_area)
        used_strata.append(stratum)  # Track which stratum was used
        
        # Calculate and append other metrics
        comm_rate, omis_rate = calculate_error_rates(stratum_df)
        commission_error_rates.append(comm_rate)
        omission_error_rates.append(omis_rate)
        n_h.append(len(stratum_df))
        p_bar_h.append(np.mean(stratum_df['landcover_code']))
    
    # Convert to numpy arrays for calculations
    strata_areas = np.array(strata_areas)
    
    # Only use proportions for strata that had data
    filtered_proportions = np.array([strata_proportions[s] for s in used_strata])
    
    adjustments = calculate_adjustments(strata_areas, commission_error_rates, 
                                     omission_error_rates, filtered_proportions)
    
    total_adjustment = np.sum(adjustments)
    adjusted_area = observed_area + total_adjustment
    
    N_h = sum(n_h)
    se = calculate_se(strata_areas, np.array(n_h), N_h, np.array(p_bar_h))
    ci_95 = 1.96 * se
    
    return {
        'observed': observed_area,
        'adjusted': adjusted_area,
        'adjustment': total_adjustment,
        'se': se,
        'ci_95': ci_95
    }

def process_years(years: range,
                 observed_df: pd.DataFrame,
                 accuracy_df: pd.DataFrame,
                 strata_proportions: np.ndarray,
                 total_area: float,
                 area_column: str) -> pd.DataFrame:
    """
    Process multiple years of cropland data for bias adjustment.

    Applies the Olofsson methodology annually to a time series of cropland
    extent estimates.

    Args:
        years: Range of years to process
        observed_df: DataFrame with annual observed areas
        accuracy_df: DataFrame with validation points
        strata_proportions: Relative size of each stratum
        total_area: Total area of the region
        area_column: Column name in observed_df containing area values

    Returns:
        DataFrame with annual bias-adjusted estimates and uncertainties
    """
    results = []
    for year in years:
        observed_area = observed_df[observed_df['year'] == year][area_column].values[0]
        year_accuracy_df = accuracy_df[accuracy_df['year'] == year]
        
        result = cropland_area_adjustment(observed_area, year_accuracy_df, 
                                        strata_proportions, total_area)
        result['year'] = year
        results.append(result)
    
    return pd.DataFrame(results)

def process_subregion(df: pd.DataFrame,
                     accuracy_df: pd.DataFrame,
                     strata_proportions: np.ndarray,
                     overlap_areas: Dict[str, float],
                     country_columns: List[str],
                     years: range,
                     is_gross: bool = True) -> Dict[str, pd.DataFrame]:
    """
    Process cropland estimates for a specific subregion (Great Plains or Southern).

    Handles regional bias adjustment for both total (gross) and active cropland
    footprints, separated by country.

    Args:
        df: DataFrame with cropland areas by country
        accuracy_df: Validation points for the subregion
        strata_proportions: Relative stratum sizes for the subregion
        overlap_areas: Dictionary of total areas by country
        country_columns: List of column names containing country-specific areas
        years: Range of years to process
        is_gross: Whether processing total (True) or active (False) footprint

    Returns:
        Dictionary of adjusted results by country
    """
    results_dict = {}
    
    for country in country_columns:
        country_code = country.split('_')[0]
        total_area = overlap_areas[country_code]
        results = process_years(years, df, accuracy_df, strata_proportions, 
                              total_area, country)
        results_dict[country_code] = results
    
    return results_dict

def combine_subregion_results(gp_results: Dict[str, pd.DataFrame],
                            mx_results: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    """
    Combine results from Great Plains and Southern subregions.

    Merges area estimates and propagates uncertainties between regions,
    handling special cases like Canada which only appears in Great Plains.

    Args:
        gp_results: Dictionary of Great Plains results by country
        mx_results: Dictionary of Southern region results by country

    Returns:
        Dictionary of combined results by country
    """
    combined_results = {}
    
    for country in gp_results.keys():
        if country == 'canada':
            combined_results[country] = gp_results[country]
        elif country in mx_results:
            combined_df = pd.DataFrame()
            combined_df['year'] = gp_results[country]['year']
            combined_df['observed'] = gp_results[country]['observed'] + mx_results[country]['observed']
            combined_df['adjusted'] = gp_results[country]['adjusted'] + mx_results[country]['adjusted']
            combined_df['adjustment'] = gp_results[country]['adjustment'] + mx_results[country]['adjustment']
            # Propagate uncertainty between regions
            combined_df['se'] = np.sqrt(gp_results[country]['se']**2 + mx_results[country]['se']**2)
            combined_df['ci_95'] = 1.96 * combined_df['se']
            combined_results[country] = combined_df
    
    return combined_results

def process_footprint(gross_df: pd.DataFrame, 
                     net_df: pd.DataFrame, 
                     gp_accuracy_df: pd.DataFrame, 
                     mx_accuracy_df: pd.DataFrame, 
                     gp_strata_proportions: np.ndarray, 
                     mx_strata_proportions: np.ndarray,
                     gp_overlap_areas: Dict[str, float],
                     mx_overlap_areas: Dict[str, float],
                     years: range) -> Dict[str, Dict[str, Dict[str, pd.DataFrame]]]:
    """
    Process both total and active cropland footprints across all regions.

    Main entry point for the bias correction workflow, handling both footprint
    types across both geographical subregions.

    Args:
        gross_df: Shorthand for "Total" or "Cumulative" cropland area estimates
        net_df: Shorthand for "Active" or "Annual" cropland area estimates
        gp_accuracy_df: Great Plains validation points
        mx_accuracy_df: Southern region validation points
        gp_strata_proportions: Relative size of Great Plains strata
        mx_strata_proportions: Relative size of Mexico strata
        gp_overlap_areas: Great Plains areas by country
        mx_overlap_areas: Southern region areas by country
        years: Range of years to process

    Returns:
        Nested dictionary containing all adjusted results:
            - First level: 'gross' or 'net' footprint
            - Second level: 'combined', 'great_plains', or 'mexico' regions
            - Third level: Country-specific results
    """
    country_columns = ['us_mill_acres', 'canada_mill_acres', 'mx_mill_acres', 'total_mill_acres']
    
    # Process gross footprint
    gp_gross_results = process_subregion(
        gross_df[gross_df['eco_region'] == 'GREAT PLAINS'],
        gp_accuracy_df, gp_strata_proportions, gp_overlap_areas,
        country_columns, years, is_gross=True
    )
    mx_gross_results = process_subregion(
        gross_df[gross_df['eco_region'] != 'GREAT PLAINS'],
        mx_accuracy_df, mx_strata_proportions, mx_overlap_areas,
        country_columns, years, is_gross=True
    )
    gross_combined_results = combine_subregion_results(gp_gross_results, mx_gross_results)
    
    # Process net footprint
    gp_net_results = process_subregion(
        net_df[net_df['eco_region'] == 'GREAT PLAINS'],
        gp_accuracy_df, gp_strata_proportions, gp_overlap_areas,
        country_columns, years, is_gross=False
    )
    mx_net_results = process_subregion(
        net_df[net_df['eco_region'] != 'GREAT PLAINS'],
        mx_accuracy_df, mx_strata_proportions, mx_overlap_areas,
        country_columns, years, is_gross=False
    )
    net_combined_results = combine_subregion_results(gp_net_results, mx_net_results)
    
    return {
        'gross': {
            'combined': gross_combined_results,
            'great_plains': gp_gross_results,
            'mexico': mx_gross_results
        },
        'net': {
            'combined': net_combined_results,
            'great_plains': gp_net_results,
            'mexico': mx_net_results
        }
    }