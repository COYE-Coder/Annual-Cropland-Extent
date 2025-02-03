# Export Pipeline

This module provides utilities for exporting Landsat time series data and training samples for the land cover classification exercise. It serves as the most upstream portion of the Annual Cropland Extent workflow. 

With reference to the paper, the code contained in the `training_export` portion corresponds to the synthetic "GLAD" data used for pre-training the model. Much more data was pulled with different training labels, but those are not public.

**NOTE**: This pipeline is not functional because the Rangeland Analysis Platform data for Mexico and Canada are not public. It is for code review purposes only. If you wish to use the same process for a related task, you may do so by removing the references to the Rangeland Analysis Platform data in Mexico. Feel free to email me at sean.carter@umt.edu if you need help with that. 


## Overview

The export pipeline consists of two main components:

1. **Regional Data Export**: Processes and exports the imagery to be used for *inference* (Landsat imagery combined with RAP vegetation cover data)
2. **Training Data Export**: Processes and exports the imagery to be used for *training* (Same as above plus a synthetic data label) 


## Usage
 Refer to `regional_export_demo.ipnyb` and `training_export_demo.ipynb`. 
 
