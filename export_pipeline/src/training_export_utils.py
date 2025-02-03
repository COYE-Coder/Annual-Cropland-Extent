"""
Utility functions for exporting training data from GLAD Global Cropland dataset.

This module provides functions to:
1. Access and process GLAD cropland labels
2. Combine Landsat imagery with RAP vegetation cover data
3. Create spatially stratified training/evaluation samples
4. Export samples as TFRecord files to Google Cloud Storage

The main workflow is handled by process_and_export_samples(), which coordinates
the entire pipeline from data processing to export task creation.

Typical usage:
    process_and_export_samples(
        geom_to_export=export_geometry,
        mexico_cover_asset=mexico_asset_path,
        conus_cover_asset=conus_asset_path,
        bucket=storage_bucket,
        training_folder=export_folder,
        training_base=training_prefix,
        eval_base=eval_prefix
    )
"""


import ee
from typing import List, Dict, Optional
from .export_utils import create_export_grids
from .landsat_utils import get_landsat_for_year

__all__ = ['get_glad_labels', 'get_rap_cover', 'construct_feature_stack',
           'create_training_stack', 'export_training_samples', 
           'process_and_export_samples']

def get_glad_labels() -> ee.ImageCollection:
    """Get GLAD cropland labels."""
    glad_labels = ee.ImageCollection.fromImages([
        ee.Image(ee.ImageCollection("users/potapovpeter/Global_cropland_2003").mosaic())
            .set('system:id', "users/potapovpeter/Global_cropland_2003"),
        ee.Image(ee.ImageCollection("users/potapovpeter/Global_cropland_2007").mosaic())
            .set('system:id', "users/potapovpeter/Global_cropland_2007"),
        ee.Image(ee.ImageCollection("users/potapovpeter/Global_cropland_2011").mosaic())
            .set('system:id', "users/potapovpeter/Global_cropland_2011"),
        ee.Image(ee.ImageCollection("users/potapovpeter/Global_cropland_2015").mosaic())
            .set('system:id', "users/potapovpeter/Global_cropland_2015"),
        ee.Image(ee.ImageCollection("users/potapovpeter/Global_cropland_2019").mosaic())
            .set('system:id', "users/potapovpeter/Global_cropland_2019")
    ])
    
    return glad_labels.map(lambda img: img.set(
        'system:time_start', 
        ee.Date(ee.String(img.get('system:id')).slice(-4).cat('-01-01')).millis()
    ))

def get_rap_cover(year: int, 
                  mexico_cover: ee.ImageCollection,
                  conus_cover: ee.ImageCollection) -> ee.Image:
    """Get RAP cover data for a specific year."""
    dateStart = f'{year}-09-01'
    dateEnd = f'{year}-11-01'
    
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

def construct_feature_stack(img: ee.Image) -> ee.Image:
    """Construct feature stack with neighborhood arrays."""
    featureStack = ee.Image(img).float()
    
    kernel_list = ee.List.repeat(1, 512)
    kernel_lists = ee.List.repeat(kernel_list, 512)
    kernel = ee.Kernel.fixed(512, 512, kernel_lists)
    
    arrays = featureStack.neighborhoodToArray(kernel)
    return arrays.set('system:time_start', 
                     ee.Date(img.get('system:time_start')).millis())

def create_training_stack(landsat_img: ee.Image,
                         rap_data: ee.Image,
                         train_data: ee.Image,
                         date_start: str) -> ee.Image:
    """Create complete training stack with all necessary bands."""
    stack = landsat_img.addBands(rap_data).clamp(0,1).toFloat()
    train_ag = train_data.eq(1).toFloat().rename("response_ag")
    
    return stack.addBands(train_ag).set(
        'system:time_start', 
        ee.Date(date_start).millis()
    )

def export_training_samples(array: ee.Image,
                          training_polys: ee.FeatureCollection,
                          year: int,
                          bucket: str,
                          folder: str,
                          training_base: str,
                          n_shards: int = 25,
                          samples_per_poly: int = 250,
                          scale: int = 30,
                          tile_scale: int = 16) -> List[ee.batch.Task]:
    """Export training samples to cloud storage."""
    tasks = []
    training_list = training_polys.toList(training_polys.size())
    total_polys = training_polys.size().getInfo()
    
    print(f"\nProcessing {total_polys} polygons for year {year}")
    
    for g in range(total_polys):
        print(f"Processing polygon {g+1}/{total_polys} for year {year}")
        geom_sample = ee.FeatureCollection([])
        
        for i in range(n_shards):
            if i % 5 == 0:  # Print progress every 5 shards
                print(f"  - Generating shard {i+1}/{n_shards}")
            sample = array.sample(
                region=ee.Feature(training_list.get(g)).geometry(),
                scale=scale,
                numPixels=samples_per_poly / n_shards,
                seed=i+100,
                tileScale=tile_scale
            )
            geom_sample = geom_sample.merge(sample)
        
        desc = f"{training_base}{year}_g{g}"
        task = ee.batch.Export.table.toCloudStorage(
            collection=geom_sample,
            description=f"glad_ag_{desc}",
            bucket=bucket,
            fileNamePrefix=f"{folder}/glad_ag_{desc}",
            fileFormat='TFRecord'
        )
        task.start()
        print(f"  Started export task: glad_ag_{desc}")
        tasks.append(task)
    
    print(f"Completed processing for year {year}. Started {len(tasks)} export tasks.\n")
    return tasks

def process_and_export_samples(
    geom_to_export: ee.Geometry,
    mexico_cover_asset: str,
    conus_cover_asset: str,
    bucket: str,
    training_folder: str,
    training_base: str,
    eval_base: str,
    grid_scale: float = 5e5
) -> None:
    """Process and export training samples for all available years."""
    # Get GLAD labels and years
    glad_labels = get_glad_labels()
    years = glad_labels.aggregate_array('system:time_start')\
        .map(lambda x: ee.Date(x).get('year')).getInfo()
    
    # Get vegetation cover data
    mexico_cover = ee.ImageCollection(mexico_cover_asset).map(
        lambda img: img.set(
            'system:time_start', 
            ee.Date(ee.String(img.get('year')).cat('-01-01')).millis()
        )
    )
    conus_cover = ee.ImageCollection(conus_cover_asset)
    
    # Process each year to create input images
    input_images_list = []
    for year in years:
        landsat = get_landsat_for_year(year)
        rap_data = get_rap_cover(year, mexico_cover, conus_cover)
        
        dateStart = f'{year}-09-01'
        startYear = f'{year}-01-01'
        endYear = f'{year+1}-01-01'
        
        train_data = ee.Image(glad_labels.filterDate(startYear, endYear).first())
        stack = create_training_stack(landsat, rap_data, train_data, dateStart)
        input_images_list.append(stack)
    
    # Create feature collection and arrays
    input_images = ee.ImageCollection.fromImages(input_images_list)
    arrays = input_images.map(construct_feature_stack)
    
    # Create grids and split into training/eval
    covering_grid, grid_size, grid_list = create_export_grids(
        geometry=geom_to_export,
        grid_scale=grid_scale,
        grid_crs="EPSG:5070"
    )
    
    grids = ee.FeatureCollection(grid_list).randomColumn()
    training_polys = grids.filter('random >= 0.2').filter('random >= 0.8')
    eval_polys = grids.filter('random < 0.2').filter('random <= 0.02')
    
    # Export samples for each year
    for year in years:
        array = ee.Image(arrays.filterDate(f'{year}-01-01', f'{year}-12-31').mosaic())
        
        # Export training data
        training_tasks = export_training_samples(
            array=array,
            training_polys=training_polys,
            year=year,
            bucket=bucket,
            folder=training_folder,
            training_base=training_base
        )
        
        # Export evaluation data
        eval_tasks = export_training_samples(
            array=array,
            training_polys=eval_polys,
            year=year,
            bucket=bucket,
            folder=training_folder,
            training_base=eval_base
        )