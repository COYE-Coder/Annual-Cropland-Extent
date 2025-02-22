# src/bias_correction/visualization.py

"""
Visualization module for cropland area estimation results.

This module provides functions to create publication-quality figures showing
cropland area trends across different regions and footprint types.
"""

import numpy as np
import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
from typing import Dict, Union
from .config import FIG_DATA_DIR


# Constants
ACRES_TO_HECTARES = 0.404686
COUNTRY_NAMES = {
    'total': 'Full Region of Interest',
    'us': 'United States of America', 
    'canada': 'Canada',
    'mx': 'Mexico'
}
COUNTRY_COLORS = {
    'total': 'black',
    'us': 'blue',
    'canada': 'red',
    'mx': 'green'
}

def calculate_trend(data: pd.DataFrame) -> tuple:
    """
    Calculate linear trend in cropland area from 2000 onwards.
    
    Args:
        data: DataFrame containing 'year' and 'adjusted' columns
        
    Returns:
        tuple: (total_change, error) in original units
    """
    data = data[data['year'] >= 2000]
    slope, intercept, r_value, p_value, std_err = stats.linregress(
        data['year'], data['adjusted']
    )
    total_change = slope * (data['year'].max() - data['year'].min())
    error = std_err * (data['year'].max() - data['year'].min())
    
    return total_change, error

def setup_xaxis(ax: plt.Axes, start_year: int, end_year: int, is_bottom: bool = False) -> None:
    """
    Configure x-axis formatting for the trend plots.
    
    Args:
        ax: Matplotlib axes object
        start_year: First year to display
        end_year: Last year to display
        is_bottom: Whether this is the bottom panel (determines label visibility)
    """
    all_years = np.arange(start_year, end_year + 1)
    major_ticks = all_years[all_years % 5 == 0]
    minor_ticks = all_years[all_years % 5 != 0]
    
    ax.set_xticks(major_ticks)
    ax.set_xticks(minor_ticks, minor=True)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{int(x)}'))
    ax.xaxis.set_minor_formatter(plt.FuncFormatter(lambda x, _: f'{int(x)}'))
    
    if is_bottom:
        ax.tick_params(axis='x', which='both', rotation=45)
        for label in ax.get_xticklabels(which='major'):
            label.set_fontweight('bold')
            label.set_fontsize(45)
        for label in ax.get_xticklabels(which='minor'):
            label.set_fontsize(35)
    else:
        ax.tick_params(axis='x', which='minor', labelbottom=False)
        ax.tick_params(axis='x', which='major', rotation=45)
        for label in ax.get_xticklabels(which='major'):
            label.set_fontweight('bold')
            label.set_fontsize(45)

def create_multipanel_plot(results: Dict, save_path: str = None) -> None:
    """
    Create a multi-panel figure showing cropland area trends.
    
    Creates a publication-quality figure showing total and active cropland
    footprint trends for different regions, including uncertainty bounds
    and trend lines.
    
    Args:
        results: Nested dictionary containing bias-corrected results
        save_path: Optional path to save the figure
        
    Returns:
        None: Displays and optionally saves the figure
    """
    countries = ['total', 'canada', 'us', 'mx']
    
    # Create figure and grid
    fig = plt.figure(figsize=(45, 60))
    gs = fig.add_gridspec(4, 2, width_ratios=[0.8, 0.2], wspace=0.05, hspace=0.2)
    
    fig.suptitle('Trends in Agricultural Footprint - Total and Active', 
                 fontsize=70, y=0.95, fontweight='bold')
    
    # Create panels for each country
    for i, country in enumerate(countries):
        ax = fig.add_subplot(gs[i, 0])
        img_ax = fig.add_subplot(gs[i, 1])
        ax.set_axisbelow(True)
        
        print(f"\nCountry: {COUNTRY_NAMES[country]}")
        
        # Plot both footprint types
        for j, (footprint_type, data_type) in enumerate([('Total', 'gross'), ('Active', 'net')]):
            data = results[data_type]['combined'][country].copy()
            
            # Calculate and convert trend
            change, error = calculate_trend(data)
            change *= ACRES_TO_HECTARES
            error *= ACRES_TO_HECTARES
            
            # Convert data to hectares
            start_value = data[data['year'] == 2000]['adjusted'].values[0] * ACRES_TO_HECTARES
            data['adjusted'] *= ACRES_TO_HECTARES
            data['se'] *= ACRES_TO_HECTARES
            
            # Create trend line
            mask_2000 = data['year'] >= 2000
            filtered_data = data[mask_2000]
            years_pred = np.linspace(2000, filtered_data['year'].max(), 100)
            slope = change / (2021 - 2000)
            y_pred = start_value + slope * (years_pred - 2000)
            
            # Plot components
            _plot_data_points(ax, data, footprint_type, country)
            _plot_uncertainty(ax, data, footprint_type, country)
            _plot_trend_line(ax, years_pred, y_pred, country)
        
        # Format panel
        _format_panel(ax, country, data, i)
        
        # Add region image
        _add_region_image(img_ax, country)
    
    # Final formatting
    plt.tight_layout()
    plt.subplots_adjust(top=0.9, bottom=0.1, left=0.08, right=0.98, hspace=0.2)
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    
    plt.show()

# Helper functions for plotting components
def _plot_data_points(ax, data, footprint_type, country):
    """Plot the actual data points with connecting lines."""
    ax.plot(data['year'], data['adjusted'], 
            'o-' if footprint_type == 'Total' else 's--', 
            label=f"{footprint_type}",
            color=COUNTRY_COLORS[country], 
            alpha=0.7 if footprint_type == 'Total' else 0.5,
            linewidth=4.0,
            markersize=10,
            zorder=3)

def _plot_uncertainty(ax, data, footprint_type, country):
    """Add uncertainty bounds."""
    ax.fill_between(data['year'], 
                   data['adjusted'] - data['se'], 
                   data['adjusted'] + data['se'], 
                   color=COUNTRY_COLORS[country], 
                   alpha=0.2 if footprint_type == 'Total' else 0.1,
                   zorder=3)

def _plot_trend_line(ax, years_pred, y_pred, country):
    """Add the trend line."""
    ax.plot(years_pred, y_pred, ':', 
            color=COUNTRY_COLORS[country], 
            alpha=1,
            linewidth=5,
            zorder=3)

def _format_panel(ax, country, data, panel_index):
    """Apply formatting to individual panel."""
    ax.set_title(COUNTRY_NAMES[country], fontsize=82, color='#3A3A3A')
    legend = ax.legend(fontsize=55, loc='upper left')
    legend.set_zorder(1)
    
    setup_xaxis(ax, data['year'].min(), data['year'].max(), 
                is_bottom=(panel_index == 3))
    
    if panel_index != 3:
        ax.tick_params(axis='x', which='both', labelbottom=False)
    
    if panel_index == 3:
        ax.set_xlabel('Year', fontsize=55, fontweight='bold')
        ax.xaxis.set_label_coords(0.5, -0.25)
    
    ax.set_ylabel('Million Hectares', fontsize=82.5, fontweight='bold')
    ax.yaxis.set_label_coords(-0.05, 0.5)
    
    ax.tick_params(axis='y', labelsize=45)
    ax.grid(True, which='major', linestyle='-', linewidth=1.5, 
            color='gray', alpha=0.5, zorder=0)
    ax.grid(True, which='minor', linestyle=':', linewidth=0.4, 
            color='gray', alpha=0.3, zorder=0)

def _add_region_image(img_ax, country):
    """Add region image to the panel."""
    if country == 'mx':
        img_country = 'mexico'
    elif country == 'us':
        img_country = 'united_states'
    else:
        img_country = country
        
    img_path = FIG_DATA_DIR / f"{country if country in ['canada','total'] else img_country}_transparent.png"
    if not img_path.exists():
        raise FileNotFoundError(f"Image file not found: {img_path}")
        
    img = plt.imread(str(img_path))
    img_ax.imshow(img)
    img_ax.axis('off')