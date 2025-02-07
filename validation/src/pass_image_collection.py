"""
This script provides functions for preprocessing and retrieving Landsat images, as well as auxiliary data.
These images are linked with the GEEMAP Google Earth Engine API in order to display the map for a given point

The script includes the following main components:
1. Image preprocessing functions: Functions for applying unit scale, scale factors, and quality masks to Landsat images.
2. Landsat image retrieval functions: Functions to retrieve Landsat images for a given year and apply preprocessing steps.
2a. Note-> This will be different sets of Landsat sensor images depending on the year. For example, prior to 1999, Landsat 5 is the only available sensor
3. Auxiliary data retrieval functions: Functions to cropland model output data from 
    Pasture Pulse (our model; 'window'), Global Cropland Extent ('GLAD'), and the Cropland Data Layer ('CDL') images for a given year.
4. Ancillary functions: Helper functions for calculating total cover and percentage of perennial forage from the Rangeland Analysis Platform output
5. Ancillary image collections and usable space model: Definitions for GLAD labels, window labels, CDL labels, and the usable space model.

Usage:
- Use the `get_index_image` function to retrieve a preprocessed "Index" image, 
        from the Soil Adjusted Vegetation Index, and Rangeland Analysis Platform data, for a specific year.
- Use the `get_landsat_image` function to retrieve a Landsat image with applied scale factors and unit scale for a specific year.
- Use the auxiliary data retrieval functions (`get_glad_image`, `get_window_image`, `get_cdl_image`) to retrieve the respective images for a specific year.

Note: Because the Rangeland Analysis Platform is a proprietary data product, it is only publicly accessible for the CONUS domain. 
        Running the `get_index_image` function without proper permission to access the RAP data in Canada and Mexico will result in an error
        If you wish to use this code, please comment out the mexico_cover and canada_cover imagecollections. 


Questions can be directed to sean.carter@umt.edu
"""

try:
    from ee_auth import initialize_earth_engine  # For running as script
except ImportError:
    from .ee_auth import initialize_earth_engine  # For running as module
import ee

initialize_earth_engine()

# Define the band names
LC89_BANDS = ['SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B6', 'SR_B7', 'QA_PIXEL']  # Landsat 8 and 9
LC57_BANDS = ['SR_B1', 'SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B7', 'QA_PIXEL']  # Landsat 5 and 7
STD_NAMES = ['blue', 'green', 'red', 'nir', 'swir1', 'swir2', 'QA_PIXEL']


# Image preprocessing functions

def apply_unit_scale(img: ee.Image) -> ee.Image:
    """
    Applies unit scale to the landsat image bands. 
    Expects the band names to be regularized to the STD_NAMES list

    Args:
        img: The input image.

    Returns:
        The image with unit scale applied to the bands.
    """
    band6 = img.select('swir2').unitScale(295, 340).clamp(0, 1).rename('swir2')
    band1 = img.select('blue').unitScale(0, 0.3).clamp(0, 1).rename('blue')
    band2 = img.select('green').unitScale(0, 0.3).clamp(0, 1).rename('green')
    band3 = img.select('red').unitScale(0, 0.4).clamp(0, 1).rename('red')
    band4 = img.select('nir').unitScale(0, 0.55).clamp(0, 1).rename('nir')
    band5 = img.select('swir1').unitScale(0, 0.55).clamp(0, 1).rename('swir1')
    QA = img.select('QA_PIXEL')

    image = ee.Image.cat([band1, band2, band3, band4, band5, band6, QA])
    return image


def apply_scale_factors(image: ee.Image) -> ee.Image:
    """
    Applies scale factors to the Landsat image bands.

    Args:
        image: The input image.

    Returns:
        The image with scale factors applied to the bands.
    """
    optical_bands = image.select(STD_NAMES).multiply(0.0000275).add(-0.2)
    thermal_band = image.select('ST_B6').multiply(0.00341802).add(149.0)
    return image.addBands(optical_bands, None, True).copyProperties(image, ['system:time_start'])


def gen_landsat_mask457(img: ee.Image) -> ee.Image:
    """
    Generates a Landsat 4, 5, and 7 quality mask.

    Args:
        img: The input Landsat image.

    Returns:
        The quality mask for Landsat 4, 5, and 7.
    """
    qa = img.select('QA_PIXEL')
    fill_bit_mask = 1 << 0
    dilated_bit_mask = 1 << 1
    cloud_bit_mask = 1 << 3
    cloud_shadow_bit_mask = 1 << 4
    snow_bit_mask = 1 << 5
    water_bit_mask = 1 << 7

    return qa.bitwiseAnd(cloud_bit_mask).eq(0).And(qa.bitwiseAnd(cloud_shadow_bit_mask).eq(0)).And(
        qa.bitwiseAnd(snow_bit_mask).eq(0)).And(qa.bitwiseAnd(fill_bit_mask).eq(0)).And(
        qa.bitwiseAnd(dilated_bit_mask).eq(0))


def gen_landsat_mask8(img: ee.Image) -> ee.Image:
    """
    Generates a Landsat 8 quality mask.

    Args:
        img: The input Landsat 8 image.

    Returns:
        The quality mask for Landsat 8.
    """
    qa = img.select('QA_PIXEL')
    cloud = qa.bitwiseAnd(1 << 5)
    cloud_conf = qa.bitwiseAnd(3 << 7)
    cirrus_conf = qa.bitwiseAnd(3 << 9)
    return cloud.eq(0).And(cloud_conf.lt(2)).And(cirrus_conf.lt(2))


def apply_mask_l8(img: ee.Image) -> ee.Image:
    """
    Applies the quality mask to a Landsat 8 image.

    Args:
        img: The input Landsat 8 image.

    Returns:
        The Landsat 8 image with the quality mask applied.
    """
    qa = img.select('QA_PIXEL')
    qa_mask = gen_landsat_mask8(qa)
    return img.updateMask(qa_mask).copyProperties(img, ['system:time_start'])


def apply_mask(img: ee.Image) -> ee.Image:
    """
    Applies the quality mask to a Landsat 4, 5, or 7 image.

    Args:
        img: The input Landsat 4, 5, or 7 image.

    Returns:
        The Landsat 4, 5, or 7 image with the quality mask applied.
    """
    qa = img.select('QA_PIXEL')
    qa_mask = gen_landsat_mask457(qa)
    return img.updateMask(qa_mask).copyProperties(img, ['system:time_start'])


def calculate_savi(img: ee.Image) -> ee.Image:
    """
    Calculates the Soil Adjusted Vegetation Index (SAVI) for an image.
    Expects STD_NAMES

    Args:
        img: The input image.

    Returns:
        The image with the SAVI band added.
    """
    savi = img.expression(
        '((nir_band - red_band) / (nir_band + red_band + 0.5)) * (1.5)',
        {
            'red_band': img.select('red'),
            'nir_band': img.select('nir')
        }
    ).rename('savi')

    return savi.addBands(img).copyProperties(img, ['system:time_start'])

def initialize_collections():
    """Initialize Landsat collections after Earth Engine authentication."""
    global ls5sr, ls7sr, ls8sr
    ls5sr = ee.ImageCollection('LANDSAT/LT05/C02/T1_L2').select(LC57_BANDS, STD_NAMES).map(apply_mask)
    ls7sr = ee.ImageCollection("LANDSAT/LE07/C02/T1_L2").select(LC57_BANDS, STD_NAMES).map(apply_mask)
    ls8sr = ee.ImageCollection("LANDSAT/LC08/C02/T1_L2").select(LC89_BANDS, STD_NAMES).map(apply_mask_l8)

initialize_collections()

# Landsat image retrieval functions
def get_landsat_ic_from_year(year: int)-> ee.ImageCollection:
    """
    Logic to receive the correct set of Landsat records. Any year after 2014 will have all three LANDSAT records.
    Examining 6 month "summer" composite

    Args: 
        year: The year for which to retrieve the appropriate Landsat ImageCollection

    Returns:
        The appropriate Landsat Collection, filtered by summer months
    
    """
    year_str = str(year)
    if year <= 1999:
        landsat_collection = ls5sr.filterDate(year_str + '-04-01', year_str + '-09-30')
    elif year <= 2014:
        landsat_collection = ls7sr.filterDate(year_str + '-04-01', year_str + '-09-30') \
            .merge(ls5sr.filterDate(year_str + '-04-01', year_str + '-09-30'))
    else:
        landsat_collection = ls8sr.filterDate(year_str + '-04-01', year_str + '-09-30') \
            .merge(ls7sr.filterDate(year_str + '-04-01', year_str + '-09-30')) \
            .merge(ls5sr.filterDate(year_str + '-04-01', year_str + '-09-30'))
        
    return landsat_collection

def get_index_image(year: int) -> ee.Image:
    """
    Retrieves the appropriate "index" image for a given year and applies preprocessing steps.
    This "index" image consists of a SAVI band and two Rangeland Analysis derivatives that are useful to visually identify current croplands

    Args:
        year: The year for which to retrieve the Landsat image.

    Returns:
        The preprocessed Landsat image for the specified year.
    """
    # Define date range and filter collections
    year_str = str(year)
    dateStart = str(year) + '-09-01'
    dateEnd = str(year) + '-11-01'

    startYear = ee.Date(dateStart).get('year').getInfo()
    endYear = ee.String(ee.Number(startYear).add(1)).getInfo()

    startYear, endYear = str(startYear) + '-01-01', str(endYear) + '-01-01'

    # This will throw an error if you do not have permission to access this ImageCollection
    mexico_cover = ee.ImageCollection('projects/wlfw-um/assets/mexico/vegetation-cover-v3').map(
        lambda img: img.set('system:time_start', ee.Date(ee.String(img.get('year')).cat('-01-01')).millis())
    ).filterDate(startYear, endYear)

    conus_cover = ee.ImageCollection('projects/rangeland-analysis-platform/vegetation-cover-v3').filterDate(startYear,
                                                                                                            endYear)

    canada_cover = ee.ImageCollection('projects/wlfw-um/assets/canada/vegetation-cover-v3').filterDate(startYear,
                                                                                                        endYear)

    rap = mexico_cover.merge(conus_cover).merge(canada_cover)
    total_cover = rap.map(calculate_total_cover).mosaic()

    pfg_pct = rap.map(calculate_pct_pfg).mosaic()

    agFilter = total_cover.subtract(pfg_pct).rename('ag_filter')

    landsat_collection = get_landsat_ic_from_year(year)

    dataset = landsat_collection.map(apply_scale_factors).median()

    savi = landsat_collection.map(apply_scale_factors) \
        .map(apply_unit_scale) \
        .map(calculate_savi).median()

    savi = savi.unitScale(-0.3, 0.3).multiply(255).toByte()
    agFilter = agFilter.unitScale(0, 100).multiply(255).toByte()

    visDataset = dataset.unitScale(0, 0.3).multiply(255).toByte().select(['red', 'green', 'blue'])

    grayscale = visDataset.expression(
        '(0.3 * R) + (0.59 * G) + (0.11 * B)',
        {
            'R': visDataset.select('red'),
            'G': visDataset.select('green'),
            'B': visDataset.select('blue')
        }
    ).rename('grayscale')
    output = grayscale.addBands(agFilter).addBands(savi).select(['grayscale', 'ag_filter', 'savi']) \
        .set("system:time_start", ee.Date.parse('yyyy', year_str))

    return output


def get_landsat_image(year: int) -> ee.Image:
    """
    Retrieves the appropriate Landsat image for a given year and applies preprocessing steps.

    Args:
        year: The year for which to retrieve the Landsat image.

    Returns:
        The preprocessed Landsat image for the specified year.
    """
    landsat_collection = get_landsat_ic_from_year(year)
    year_str = str(year)

    landsat_collection = landsat_collection.map(apply_scale_factors) \
                                           .map(apply_unit_scale)\
                                           .map(calculate_savi)
    
    landsat_image = landsat_collection.median().set("system:time_start", ee.Date.parse('yyyy', year_str))
    return landsat_image


# Auxiliary data retrieval functions

def get_glad_image(year: int) -> ee.ImageCollection:
    """
    Retrieves the GLAD image for a given year.

    Args:
        year: The year for which to retrieve the GLAD image.

    Returns:
        The GLAD image collection for the specified year.
    """
    year_str = str(year)
    image = glad_labels.filterDate(year_str + '-01-01', year_str + '-12-31')
    return image


def get_window_image(year: int) -> ee.ImageCollection:
    """
    Retrieves the window image for a given year.

    Args:
        year: The year for which to retrieve the window image.

    Returns:
        The window image collection for the specified year.
    """
    year_str = str(year)
    image = window_labels.filterDate(year_str + '-01-01', year_str + '-12-31')
    return image


def get_cdl_image(year: int) -> ee.ImageCollection:
    """
    Retrieves the CDL (Cropland Data Layer) image for a given year.

    Args:
        year: The year for which to retrieve the CDL image.

    Returns:
        The CDL image collection for the specified year.
    """
    year_str = str(year)
    image = cdl_labels.filterDate(year_str + '-01-01', year_str + '-12-31')
    return image


# Ancillary functions

def calculate_total_cover(img: ee.Image) -> ee.Image:
    """
    Calculates the total cover for an image.

    Args:
        img: The input image.

    Returns:
        The image with the total cover band added.
    """
    total_cover = img.select(0) \
        .add(img.select(1)) \
        .add(img.select(2)) \
        .add(img.select(3)) \
        .add(img.select(4)) \
        .add(img.select(5))

    return total_cover.rename(['totalCover']) \
        .copyProperties(img, ['system:time_start', 'year'])


def calculate_pct_pfg(img: ee.Image) -> ee.Image:
    """
    Calculates the percentage of perennial forage for an image.

    Args:
        img: The input image.

    Returns:
        The image with the percentage of perennial forage band added.
    """
    total_cover = img.select(0) \
        .add(img.select(1)) \
        .add(img.select(2)) \
        .add(img.select(3)) \
        .add(img.select(4)) \
        .add(img.select(5))

    pfg = img.select('PFG').divide(total_cover).multiply(100)
    shr = img.select('SHR').lte(6)
    afg = img.select('AFG').lte(6)
    ltr = img.select('LTR').lte(6)

    return pfg.multiply(shr).multiply(afg).multiply(ltr) \
        .rename(['PctPFG']) \
        .copyProperties(img, ['system:time_start', 'year'])


def remap_croplands(image: ee.Image) -> ee.Image:
    """
    Remaps the cropland values in the image.

    Args:
        image: The input image.

    Returns:
        The remapped image with croplands mapped to 1 and non-croplands mapped to 0.
    """
    remapped = image.remap(from_values, to_values, 0)

    return remapped

# Define constants
from_values = [
    # Croplands
    1, 2, 3, 4, 5, 6, 10, 11, 12, 13, 14, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 
    31, 32, 33, 34, 35, 36, 37, 38, 39, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 
    51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 204, 205, 206, 207, 208, 209, 210, 
    211, 212, 213, 214, 215, 216, 217, 218, 219, 220, 221, 222, 223, 224, 225, 
    226, 227, 228, 229, 230, 231, 232, 233, 234, 235, 236, 237, 238, 239, 240, 241, 242, 243, 244, 245, 246, 247, 248, 249, 250, 254,
    # Natural
    63, 64, 65, 141, 142, 143, 152, 176, 190, 195,
    # Fallow
    61
]

to_values = ee.List.repeat(1, 98).cat(ee.List.repeat(0, 10)).add(0)  # Mapping natural and fallow to 0, as we want a binary layer for croplands


# Ancillary image collections

glad_labels = ee.ImageCollection.fromImages([
    ee.Image(ee.ImageCollection("users/potapovpeter/Global_cropland_2003").mosaic()).set('system:id', "users/potapovpeter/Global_cropland_2003"),
    ee.Image(ee.ImageCollection("users/potapovpeter/Global_cropland_2007").mosaic()).set('system:id', "users/potapovpeter/Global_cropland_2007"),
    ee.Image(ee.ImageCollection("users/potapovpeter/Global_cropland_2011").mosaic()).set('system:id', "users/potapovpeter/Global_cropland_2011"),
    ee.Image(ee.ImageCollection("users/potapovpeter/Global_cropland_2015").mosaic()).set('system:id', "users/potapovpeter/Global_cropland_2015"),
    ee.Image(ee.ImageCollection("users/potapovpeter/Global_cropland_2019").mosaic()).set('system:id', "users/potapovpeter/Global_cropland_2019")
])

glad_labels = glad_labels.map(lambda img: img.set('system:time_start', ee.Date(ee.String(img.get('system:id')).slice(-4).cat('-01-01')).millis()))

window_labels = ee.ImageCollection('projects/wlfw-um/assets/mexico/ag_mv_win')

# Receive the true ROI for CDL model, to compare apples to apples 

useable_space = ee.ImageCollection('projects/wlfw-um/assets/mexico/useable_space_tack')

mask = useable_space.first().select(['ag', 'urb']).add(1).gt(0)

# Update the mask to exclude the zero values
zones = mask.updateMask(mask.neq(0))

# Convert the zones of the thresholded landcover to vectors.
vectors = zones.reduceToVectors(
    geometry=useable_space.first().geometry(),
    scale=1000,  # Choose an appropriate scale for your dataset
    geometryType='polygon',
    eightConnected=False,
    labelProperty='zone',
    reducer=ee.Reducer.sum(),
    maxPixels=1e8
)

# Optionally, combine the polygons to get the overall boundary (if needed).
combinedBoundaries = vectors.geometry().dissolve(100)

# Store the combinedBoundaries in an Earth Engine geometry object called true_roi
true_roi = combinedBoundaries

cdl = ee.ImageCollection("USDA/NASS/CDL")

# Apply the remapping function to each image in the CDL collection.
cdl_labels = cdl.map(remap_croplands).map(lambda x: x.rename(['cultivated']).clip(true_roi))



