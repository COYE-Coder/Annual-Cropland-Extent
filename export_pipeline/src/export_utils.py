"""
Utility functions for exporting Landsat and RAP vegetation cover data.

This module provides functions to:
1. Process and merge RAP vegetation cover data from Mexico and CONUS
2. Create spatially stratified export grids
3. Export Earth Engine images to assets
4. Process and export regional Landsat time series with RAP data

The main workflow is handled by process_and_export_regional(), which coordinates
the entire pipeline from data processing to export task creation.

Functions:
    get_rap_cover: Process and merge RAP vegetation cover data
    create_export_grids: Create spatially stratified grid for exports
    export_image_to_asset: Export an Earth Engine image to an asset
    process_and_export_regional: Process and export regional time series data

Typical usage:
    process_and_export_regional(
        geom_to_export=export_geometry,
        mexico_cover_asset=mexico_asset_path,
        conus_cover_asset=conus_asset_path,
        output_asset_path=output_path,
        start_year=2003,
        end_year=2020
    )
"""
import ee
from typing import List, Union
from .landsat_utils import get_landsat_for_year

__all__ = ['create_export_grids', 'export_image_to_asset', 
           'process_and_export_regional', 'get_rap_cover']

# Add get_rap_cover function
def get_rap_cover(year: int, 
                  mexico_cover: ee.ImageCollection,
                  conus_cover: ee.ImageCollection) -> ee.Image:
    """Get RAP cover data for a specific year."""
    startYear = str(year) + '-01-01'
    endYear = str(year + 1) + '-01-01'
    
    mx_cover = mexico_cover.filterDate(startYear, endYear)
    cn_cover = conus_cover.filterDate(startYear, endYear)
    
    cover = mx_cover.merge(cn_cover)
    
    return cover.map(lambda img: img.select('AFG').add(img.select('PFG'))
                    .addBands(img.select('TRE').add(img.select('SHR')))
                    .addBands(img.select('BGR').add(img.select('LTR')))
                    .divide(100)
                    .rename('grass','woody','ground')
                    .copyProperties(img, ['system:time_start'])
                    .copyProperties(img, ['year'])).mosaic()


def create_export_grids(geometry: ee.Geometry, 
                       grid_scale: float = 5e5,
                       grid_crs: str = "EPSG:5070") -> tuple:
    """Create covering grid for exports."""
    covering_grid = geometry.coveringGrid(grid_crs, grid_scale)
    covering_grid_size = covering_grid.size().getInfo()
    covering_grid_list = covering_grid.toList(covering_grid_size)
    
    return covering_grid, covering_grid_size, covering_grid_list

def export_image_to_asset(image: ee.Image,
                         asset_path: str,
                         region: ee.Geometry,
                         description: str,
                         scale: int = 30,
                         crs: str = 'EPSG:5070',
                         max_pixels: int = 1e13) -> ee.batch.Task:
    """Export an image to an Earth Engine asset."""
    task = ee.batch.Export.image.toAsset(
        image=image,
        description=description,
        assetId=asset_path,
        region=region,
        scale=scale,
        crs=crs,
        maxPixels=max_pixels)
    
    task.start()
    return task

def process_and_export_regional(
    geom_to_export: ee.Geometry,
    mexico_cover_asset: str,
    conus_cover_asset: str,
    output_asset_path: str,
    start_year: int = 2003,
    end_year: int = 2020,
    grid_scale: float = 5e5
) -> None:
    """Process and export regional Landsat time series data.
    
    Args:
        geom_to_export: Export region geometry
        mexico_cover_asset: Path to Mexico RAP asset
        conus_cover_asset: Path to CONUS RAP asset
        output_asset_path: Base path for output assets
        start_year: First year to process
        end_year: Last year to process (exclusive)
        grid_scale: Size of export grid cells in meters
    """
    # Create export grids
    covering_grid, grid_size, grid_list = create_export_grids(
        geometry=geom_to_export,
        grid_scale=grid_scale,
        grid_crs="EPSG:5070"
    )
    
    # Get vegetation cover data
    mexico_cover = ee.ImageCollection(mexico_cover_asset).map(
        lambda img: img.set(
            'system:time_start', 
            ee.Date(ee.String(img.get('year')).cat('-01-01')).millis()
        )
    )
    conus_cover = ee.ImageCollection(conus_cover_asset)
    
    # Process each year
    for year in range(start_year, end_year):
        print(f"\nProcessing year {year}")
        
        # Get Landsat composite
        landsat = get_landsat_for_year(year)
        
        # Get RAP cover data
        rap_data = get_rap_cover(year, mexico_cover, conus_cover)
        
        # Create final stack
        stack = landsat.addBands(rap_data).float()
        
        # Export each grid cell
        for i in range(grid_size):
            grid_geom = ee.Feature(grid_list.get(i)).geometry()
            
            desc = f"landsat_rap_{year}_grid{i}"
            asset_path = f"{output_asset_path}/{desc}"
            
            task = export_image_to_asset(
                image=stack,
                asset_path=asset_path,
                region=grid_geom,
                description=desc
            )
            
            print(f"Started export task for grid {i+1}/{grid_size}")
