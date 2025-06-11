# Annual Cropland Extent

## A high-resolution (30-m), annual cropland extent product for North America's Grasslands (1996-2021)

Agricultural land use conversion represents the largest transformation of Earth's land surface and significantly impacts carbon emissions, freshwater availability, biodiversity, and conservation. While numerous datasets quantify the area of active crop production over time, few reveal the extent to which the cumulative footprint of cropland agriculture has fragmented and diminished intact terrestrial ecosystems.

Using a convolutional neural network architecture (Attention U-Net), we estimate the change in the cumulative agricultural footprint over the North American central grasslands annually from 1996 to 2021. This region spans:

- The Great Plains of Canada
- The Great Plains of the United States
- Most of the Southern Semi-Arid Highlands and North American Deserts ecoregions of Mexico

Our study area encompasses the entire central North American flyway, which is crucial for the migration and wintering habitat of imperiled grassland birds.

### Key Findings

- We estimate that the combined cropland footprint expanded by about 20 million hectares over 20 years.
- In the Mexican portion of our study area, we estimate cropland expansion to be about 1.6 million hectares.
- In the Great Plains, our data, consistent with other studies, indicate that although actively cropped area has declined, the overall cumulative footprint of cropland continues to expand.

Our map highlights the long-term trajectory of the central North American cropland footprint across political boundaries, with important applications for rural livelihoods, conservation policy, and biodiversity protection.

## Organization
- Due to patchy data availability and permissions, this is not intended to be a working repository. Rather, the submodules contained are intended to demonstrate the analysis pipeline. Each submodule is a disparate entity indicating the four major portions of the analysis pipeline. These correspond roughly to the major sections of the Methods in the below preprint.
- 
- Generally, the pipeline follows the below sequence (with corresponding `submodule name`):
  -  EXPORT_DATA `export_pipeline` --> TRAIN MODEL AND RUN INFERENCE `training_inference` --> VALIDATE MODEL `validation` --> CORRECT FOR SYSTEMATIC BIAS `bias_correction`
 
- For more details on the scientific product, please refer to [this preprint article](https://www.biorxiv.org/content/10.1101/2025.03.18.643874v1) (to be published summer 2025). 

## Model Pretraining and Fine-Tuning

- Pretrained on the Global Cropland Expansion product (Potapov et al. 2021)
- Fine-tuned using a set of 30 manually digitized training chips
- Initial accuracy results demonstrate relative consistency with existing data products, including:
  - USDA Cropland Data Layer (USDA-NASS, 2021)
  - Global Land Analysis and Discovery Cropland data product (Potapov et al. 2021)


## Visualization

For a visualization of the dataset, please refer to this [Google Earth Engine Link](https://wlfw-um.projects.earthengine.app/view/cropland-extent-map)

## Citations

<font size="2" color="#808080">

Jones, M. O., Robinson, N. P., Naugle, D. E., Maestas, J. D., Reeves, M. C., Lankston, R. W., & Allred, B. W. (2020). Annual and 16-day rangeland production estimates for the western United States. bioRxiv, 2020.11.06.343038. http://dx.doi.org/10.1101/2020.11.06.343038

Potapov, P., Turubanova, S., Hansen, M. C., Tyukavina, A., Zalles, V., Khan, A., Song, X.-P., Pickens, A., Shen, Q., & Cortez, J. (2021). Global maps of cropland extent and change show accelerated cropland expansion in the 21st century. Nature Food.

USDA-NASS. (2021). USDA National Agricultural Statistics Service Cropland Data Layer. Published crop-specific data layer [Online]. Available at https://nassgeodata.gmu.edu/CropScape/ (accessed April 20, 2023). USDA-NASS, Washington, DC.

</font>
