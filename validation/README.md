# Crop-Scope Validation Pipeline

This directory contains the code and resources for the agriculture validation protocol used to assess the accuracy of our Crop Scope data product.

## Overview

The validation pipeline is designed to evaluate the performance of our cropland extent model by comparing its predictions against manually labeled reference data. The pipeline consists of several Python scripts and a Jupyter notebook that facilitate the validation process. A sample of the chips is provided in the data folder, although the total amount of chips is too large to be uploaded to Github. Once we have visually interpreted the chips, we can use the resultant accuracy data to correct for systematic model bias. The code for the bias correction can be found in `/../bias_correction/`.

## Validation Methodology

Our validation technique is largely influenced by the _Sample Analysis_ methodology presented in Potapov et al. (2022). We divided our region of interest into ecoregions using the [Level 1 ecoregion dataset](https://www.epa.gov/eco-research/ecoregions-north-america). Within each ecoregion, we leveraged our model output to sample areas within each of the five strata:

1. **Stable croplands**: Areas where at least 20 out of 26 images predict cropland.
2. **Cropland gain**: Regions where our model predicts cropland in 2021 but not in 1995.
3. **Cropland loss**: Regions where our model predicts cropland in 1995 but not in 2021.
4. **Possible errors**: Areas where at least 5 out of 26 images have predicted cropland values between 0.25 and 0.75.
5. **Likely non-cropland**: Areas where at least 20 out of 26 images do not predict cropland.

For each of the five strata within the GREAT PLAINS Level 1 ecoregion, we sampled 40 points for every year between 1995 and 2021. The sampled points were then visually interpreted by an image analyst using a context window of 512 x 512 pixels and three images: a Landsat false-color composite, a Landsat true-color composite, and a hybrid Landsat / Rangeland Analysis Platform index created for labeling the training images. The Landsat portion of both images represented a median composite of all images captured between Julian day 91 and 273 (April 1 and September 30, respectively). If the 30 m imagery was insufficient to identify the landcover at a given point, a modern high resolution basemap was provided, although this was used with a grain of salt, as we were hoping to identify historic landcover, not modern landcover. All other ecoregions encompassing our dataset were validated according to the same workflow, although this repository only includes the GREAT PLAINS data. 

## Repository Structure

The validation directory contains the following files and subdirectories:

- `work_notebook.ipynb`: A Jupyter notebook that interacts with the index processing and pass image collection scripts to facilitate the validation process.
- `src/`: A directory containing the source code for the validation pipeline.
  - `index_processing.py`: A Python script that processes the sampled points and generates validation data.
  - `pass_image_collection.py`: A Python script that handles the retrieval and preprocessing of Landsat and RAP images.
  - `chip_pipeline.py`: A Python script that handles the asynchronous downloading and geospatial conversion of image chips.
  - `ee_auth.py`: A utility script for Google Earth Engine authentication and initialization.
  - `config.py`: A configuration file that stores the path to the GeoJSON file containing the sampled points.
- `data/`: A directory containing the input data for the validation pipeline.
  - `ag_validation_stratifiedSamples_full_coverage_geo.geojson`: A GeoJSON file containing the sampled points for validation.

## Workflow Diagram

```mermaid
  %%{init: {
    'theme': 'base',
    'themeVariables': {
      'primaryColor': '#b3e0ff',
      'primaryTextColor': '#000',
      'primaryBorderColor': '#7AA7C7',
      'lineColor': '#7AA7C7',
      'secondaryColor': '#ffe0b3',
      'tertiaryColor': '#fff',
      'fontSize': '20px'
    }
  }}%%
  
  flowchart TB
      subgraph InputData[" 📊 INPUT DATA "]
          direction LR
          style InputData fill:#e6f3ff,stroke:#7AA7C7,stroke-width:4px
          
          GeoJSON["GeoJSON Points<br/><i>Stratified samples<br/>by ecoregion</i>"]
          LandsatIC["Landsat Images<br/><i>Surface reflectance<br/>collections</i>"]
          RAPData["RAP Data<br/><i>Rangeland Analysis<br/>Platform</i>"]
      end
  
      subgraph Process[" ⚙️ IMAGE PROCESSING"]
          direction TB
          style Process fill:#fff5e6,stroke:#D4A76A,stroke-width:15px
          
          subgraph ChipPipeline["Chip Generation"]
              direction TB
              style ChipPipeline fill:#fffbf0,stroke:#D4A76A,stroke-width:2px
              
              Filter["Filter Images<br/>Apr-Sep Composite"] --> 
              Download["Async Download<br/>Three Band Combos"] -->
              Convert["Convert to<br/>GeoTIFF"]
          end
  
          subgraph Validation["Visual Interpretation"]
              direction TB
              style Validation fill:#fffbf0,stroke:#D4A76A,stroke-width:2px
              
              Display["Display Three<br/>Image Types"] -->
              Interpret["Manual Point<br/>Interpretation"] -->
              Record["Record Land<br/>Cover Class"]
          end
      end
  
      subgraph Results[" 📈 RESULTS"]
          direction TB
          style Results fill:#e6ffe6,stroke:#79B779,stroke-width:4px
          
          CSV["Validation CSV<br/><i>Point-based results</i>"]
          Analysis["Accuracy Analysis<br/><i>By strata & region</i>"]
          
          CSV --> Analysis
      end
  
      GeoJSON --> ChipPipeline
      LandsatIC & RAPData --> Filter
      Convert --> Display
      Record --> CSV
  
      classDef default fontSize:16px;
      classDef process fill:#f9f9f9,stroke:#666,stroke-width:2px;
      classDef box fill:#fff,stroke:#333,stroke-width:2px;
  ```


## Usage

To use the validation pipeline:

0. (Optional) - use `chip_pipeline.py` in order to pull a series of different validation points asynchronously. Sample useage:
 ```python chip_pipeline.py --output_dir {YOUR_LOCAL_DIR} --num_chips_per_year 10 --start_year 2000 --end_year 2002```

1. Open the `work_notebook.ipynb` Jupyter notebook and follow the instructions to run the validation process. The notebook will guide you through the steps of loading the sampled points, retrieving the corresponding Landsat and RAP images, and performing visual interpretation.

2. The validation results will be stored in CSV files within the `work_notebook.ipynb` notebook.

## References

- Potapov, P., Turubanova, S., Hansen, M. C., Tyukavina, A., Zalles, V., Khan, A., Song, X.-P., Pickens, A., Shen, Q., & Cortez, J. (2022). Global maps of cropland extent and change show accelerated cropland expansion in the 21st century. _Nature Food_, 3(1), 19-28. [https://doi.org/10.1038/s43016-021-00429-z](https://doi.org/10.1038/s43016-021-00429-z)

## Contact

If you have any questions or suggestions regarding the validation pipeline, please contact sean.carter@umt.edu.
