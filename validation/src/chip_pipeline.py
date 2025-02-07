"""
This script processes Landsat imagery chips by fetching images, converting them to GeoTIFF format,
and saving them to a specified output directory. It supports asynchronous image fetching and conversion.

If you are brave, you can use this to export wall-to-wall tifs given a regularly spaced grid of points
(loaded with tuples_list or the `stratified_sample.geojson` file). Otherwise, it is an exercise in 
exporting thousands of small (~256 x 256) chips from a given landsat image. 
"""

import os
import argparse
from pass_image_collection import get_index_image, get_landsat_image
from config import OUTPUT_DIR, geolookup_list
import ee
from datetime import timedelta
import aiohttp
import asyncio
import time
import rasterio
from rasterio.transform import from_origin
from rasterio.crs import CRS
from PIL import Image
import numpy as np

# String representation of EPSG:4326. To be used in conversion to tif
WKT_STRING = '''GEOGCS["WGS 84",
    DATUM["WGS_1984",
        SPHEROID["WGS 84",6378137,298.257223563,
            AUTHORITY["EPSG","7030"]],
        AUTHORITY["EPSG","6326"]],
    PRIMEM["Greenwich",0,
        AUTHORITY["EPSG","8901"]],
    UNIT["degree",0.0174532925199433,
        AUTHORITY["EPSG","9122"]],
    AUTHORITY["EPSG","4326"]]'''

BUFFER_SIZE = 0.0001  # Adjust as needed


def parse_args():
    """
    Parse command-line arguments.
    """
    parser = argparse.ArgumentParser(description='Process Landsat imagery chips')
    parser.add_argument('--output_dir', type=str, default=OUTPUT_DIR,
                        help='Output directory for the chips (default: from config.py)')
    parser.add_argument('--num_chips_per_year', type=int, help='Number of chips to process per year (optional)')
    parser.add_argument('--start_year', type=int, default=1996, help='Start year (default: 1996)')
    parser.add_argument('--end_year', type=int, default=2022, help='End year (default: 2022)')
    return parser.parse_args()


async def fetch_and_convert_image(session: aiohttp.ClientSession, url: str, filename: str,
                                  coords: list, index: int) -> None:
    """
    Asynchronously fetch image and convert to GeoTIFF.
    """
    async with session.get(url) as response:
        if response.status != 200:
            raise Exception(f"Failed to fetch {url}: {response.status}")

        # First save the PNG
        png_data = await response.read()
        with open(filename, 'wb') as f:
            f.write(png_data)

        # Now convert to GeoTIFF
        filename_parts = filename.split('_')
        new_filename = '_'.join(filename_parts[:3] + filename_parts[4:])
        tif_filename = new_filename.replace('.png', '.tif')
        
        img = Image.open(filename)
        np_img = np.array(img)
        
        # Get image dimensions
        nrows, ncols, nband = np_img.shape

        # Define the region as a buffer around the point
        region = [
            coords[0] - BUFFER_SIZE,
            coords[1] - BUFFER_SIZE,
            coords[0] + BUFFER_SIZE,
            coords[1] + BUFFER_SIZE
        ]

        # Define transform and metadata
        transform = rasterio.transform.from_bounds(*region, ncols, nrows)
        metadata = {
            'driver': 'GTiff',
            'height': nrows,
            'width': ncols,
            'count': nband,
            'dtype': str(np_img.dtype),
            'crs': CRS.from_wkt(WKT_STRING),
            'transform': transform
        }

        # Write GeoTIFF
        with rasterio.open(tif_filename, 'w', **metadata) as dst:
            for j in range(nband):
                dst.write(np_img[:, :, j], j + 1)

        # Optionally remove the PNG file if you don't need it
        os.remove(filename)


async def get_result_async(index: int, point: ee.Geometry.Point, year: int, strata: int,
                           output_dir: str, coords: list) -> None:
    """
    Asynchronously handle multiple image downloads.
    """
    # Buffer the point by half the desired dimensions to create a region
    region = point.buffer(15360 / 2).bounds()

    # Get all three images and their visualization parameters
    index_image = get_index_image(year).clip(region).visualize(
        bands=['grayscale', 'ag_filter', 'savi'],
        gamma=0.37
    )

    landsat_image = get_landsat_image(year)
    false_color = landsat_image.clip(region).visualize(
        bands=['nir', 'red', 'green'],
        min=0,
        max=1
    )

    true_color = landsat_image.clip(region).visualize(
        bands=['red', 'green', 'blue'],
        min=0,
        max=1
    )

    # Get all URLs at once
    urls_and_files = [
        (index_image.getThumbURL({'region': region.getInfo(), 'dimensions': '512x512', 'format': 'png'}),
         os.path.join(output_dir, f'tile_{index:05d}_{year}_{strata}_index.png')),
        (false_color.getThumbURL({'region': region.getInfo(), 'dimensions': '512x512', 'format': 'png'}),
         os.path.join(output_dir, f'tile_{index:05d}_{year}_{strata}_falsecolor.png')),
        (true_color.getThumbURL({'region': region.getInfo(), 'dimensions': '512x512', 'format': 'png'}),
         os.path.join(output_dir, f'tile_{index:05d}_{year}_{strata}_truecolor.png'))
    ]

    async with aiohttp.ClientSession() as session:
        tasks = [
            fetch_and_convert_image(session, url, filename, coords, index)
            for url, filename in urls_and_files
        ]
        await asyncio.gather(*tasks)


def main():
    """
    Main function to process Landsat imagery chips.
    """
    start_time = time.time()
    args = parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    points_to_process = geolookup_list[:args.num_chips_per_year] if args.num_chips_per_year else geolookup_list
    years_to_export = list(range(args.start_year, args.end_year + 1))

    total_chips = len(points_to_process) * len(years_to_export)
    processed_chips = 0

    print(f"Starting to process {total_chips} chips...")

    # Create event loop
    loop = asyncio.get_event_loop()

    for year in years_to_export:
        for entry in points_to_process:
            point, strata, index = entry[0], int(entry[1]), int(entry[2])
            try:
                loop.run_until_complete(
                    get_result_async(
                        index,
                        ee.Geometry.Point(point),
                        year,
                        strata,
                        args.output_dir,
                        point  # Pass the coordinates
                    )
                )

                processed_chips += 1

                avg_time_per_chip = (time.time() - start_time) / processed_chips
                remaining_chips = total_chips - processed_chips
                est_time_remaining = timedelta(seconds=int(avg_time_per_chip * remaining_chips))

                print(f"Processed {processed_chips}/{total_chips} chips. "
                      f"Est. time remaining: {est_time_remaining}")

            except Exception as e:
                print(f"Failed to get result for index {index} and year {year}. Error: {str(e)}")

    end_time = time.time()
    total_time = timedelta(seconds=int(end_time - start_time))
    print(f"\nTotal processing time: {total_time}")
    print(f"Average time per chip: {timedelta(seconds=int((end_time - start_time) / total_chips))}")


if __name__ == "__main__":
    main()