# Bias Correction for Cropland Area Estimation

This package implements the Olofsson et al. (2014) methodology for bias-adjusted area estimation using stratified sampling. It was developed to process cropland extent analysis across the North American Central Flyway region, specifically handling both Great Plains and Southern (Mexican) subregions.

## Methods

The package implements a stratified sampling approach for bias correction of cropland area estimates. Following Olofsson et al. (2014), it:
- Calculates error-adjusted area estimates for cropland and non-cropland
- Accounts for commission and omission errors
- Weighs by proportional area of each stratum
- Computes uncertainty estimates

The methodology was applied independently to two subregions (Great Plains and Southern) and then combined to generate final area estimates and associated uncertainties for the entire study area.

## Installation

```bash
pip install git+https://github.com/yourusername/bias_correction.git



## Usage

import bias_correction as bc

# Process both total and active footprints
results = bc.process_footprint(
    gross_df=window_gross_df,
    net_df=window_net_df,
    gp_accuracy_df=gp_accuracy_df,
    mx_accuracy_df=mx_accuracy_df,
    gp_strata_proportions=bc.GP_STRATA_PROPORTIONS,
    mx_strata_proportions=bc.MX_STRATA_PROPORTIONS,
    gp_overlap_areas=bc.GP_OVERLAP_AREAS,
    mx_overlap_areas=bc.MX_OVERLAP_AREAS,
    years=bc.YEARS
)

# Create visualization
bc.create_multipanel_plot(results, save_path='trends.png')


See `demo.ipynb` for a complete example.

## Citation
If you use this code in your research, please cite:
[]


## References
Olofsson, P., Foody, G. M., Herold, M., Stehman, S. V., Woodcock, C. E., & Wulder, M. A. (2014). Good practices for estimating area and assessing accuracy of land change. Remote Sensing of Environment, 148, 42-57.