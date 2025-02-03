import ee

# Band definitions
LC89_BANDS = ['SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B6', 'SR_B7', 'QA_PIXEL']  # Landsat 8 and 9
LC57_BANDS = ['SR_B1', 'SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B7', 'QA_PIXEL']  # Landsat 5 and 7
STD_NAMES = ['blue', 'green', 'red', 'nir', 'swir1', 'swir2', 'QA_PIXEL']

def scale_factor_std_names(image):
    """Apply scaling factors to standardized band names."""
    optical_bands = image.select(['blue','green','red',
                                'nir', 'swir1','swir2']).multiply(0.0000275).add(-0.2)
    return image.addBands(optical_bands, None, True).copyProperties(image, ['system:time_start'])

def gen_landsat_mask457(img):
    """Generate mask for Landsat 4-5-7."""
    qa = img.select('QA_PIXEL')
    fill_bit_mask = 1 << 0
    dilated_bit_mask = 1 << 1
    cloud_bit_mask = 1 << 3
    cloud_shadow_bit_mask = 1 << 4
    snow_bit_mask = 1 << 5
    water_bit_mask = 1 << 7

    return qa.bitwiseAnd(cloud_bit_mask).eq(0)\
             .And(qa.bitwiseAnd(cloud_shadow_bit_mask).eq(0))\
             .And(qa.bitwiseAnd(snow_bit_mask).eq(0))\
             .And(qa.bitwiseAnd(fill_bit_mask).eq(0))\
             .And(qa.bitwiseAnd(dilated_bit_mask).eq(0))

def gen_landsat_mask8(img):
    """Generate mask for Landsat 8."""
    qa = img.select('QA_PIXEL')  
    cloud_shadow_bit_mask = 1 << 3
    cloud_bit_mask = 1 << 5
    snow_bit_mask = 1 << 4

    return qa.bitwiseAnd(cloud_shadow_bit_mask).eq(0)\
             .And(qa.bitwiseAnd(cloud_bit_mask).eq(0))\
             .And(qa.bitwiseAnd(snow_bit_mask).eq(0))

def apply_mask_l8(img):
    """Apply Landsat 8 mask."""
    qa = img.select('QA_PIXEL')
    qa_mask = gen_landsat_mask8(qa)
    return img.updateMask(qa_mask).copyProperties(img, ['system:time_start'])

def apply_mask(img):
    """Apply Landsat 4-5-7 mask."""
    qa = img.select('QA_PIXEL')
    qa_mask = gen_landsat_mask457(qa)
    return img.updateMask(qa_mask).copyProperties(img, ['system:time_start'])

def calc_index(img):
    """Calculate spectral indices."""
    ndvi = img.normalizedDifference(['nir','red']).rename(['ndvi'])
    nbr2 = img.normalizedDifference(['swir1','swir2']).rename(['nbr2'])
    ndmi = img.normalizedDifference(['nir','swir1']).rename(['ndmi'])
    
    return ndvi.addBands(nbr2).addBands(ndmi)\
              .rename('ndvi','nbr2','ndmi')\
              .copyProperties(img, ['system:time_start'])

def apply_unit_scale(img):
    """Apply unit scaling to indices."""
    band_nbr2 = img.select('nbr2').unitScale(-0.19096022810848037, 0.6268905281346331).rename('nbr2')
    band_ndmi = img.select('ndmi').unitScale(-0.4755525346720296, 0.8236820337025085).rename('ndmi')
    band_ndvi = img.select('ndvi').unitScale(-0.6114981075492081, 1.2971638445832843).rename('ndvi')

    return ee.Image(band_nbr2.addBands(band_ndmi).addBands(band_ndvi).rename(['nbr2', 'ndmi', 'ndvi']))

def get_landsat_for_year(year):
    """Get Landsat imagery for a specific year."""
    dateStart = ee.Date(str(year) + '-08-01')
    dateEnd = ee.Date(str(year) + '-11-30')

    ls5 = ee.ImageCollection('LANDSAT/LT05/C02/T1_L2').select(LC57_BANDS, STD_NAMES).filterDate(dateStart, dateEnd)
    ls7 = ee.ImageCollection("LANDSAT/LE07/C02/T1_L2").select(LC57_BANDS, STD_NAMES).filterDate(dateStart, dateEnd)
    ls8 = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2').select(LC89_BANDS, STD_NAMES).filterDate(dateStart, dateEnd).map(apply_mask_l8)

    if year < 1999:
        dataset = ls5.map(apply_mask).map(scale_factor_std_names)
    elif year < 2013:
        dataset = ls5.merge(ls7).map(apply_mask).map(scale_factor_std_names)
    else:
        ls8_prep = ls8.map(scale_factor_std_names)
        dataset = ls7.map(apply_mask).merge(ls8_prep)

    return apply_unit_scale(dataset.map(calc_index).max())