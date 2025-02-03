import ee
from typing import List, Union

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