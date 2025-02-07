# Cropland Mapping Training and Inference Pipeline

This package contains the training and inference pipeline for generating annual 30-m resolution cropland extent maps using an Attention U-Net convolutional neural network. The pipeline processes Landsat spectral indices and Rangeland Analysis Platform vegetation data to classify cropland across central North America.

## Overview

The pipeline consists of two main components:
1. A model training workflow that can be used to implement the four-stage training strategy
2. A regional inference pipeline that processes tiled segments ("chunks")

### Input Features
- Landsat-derived spectral indices (NDVI, NBR, NDMI)
- Rangeland Analysis Platform (RAP) fractional cover layers
  - Annual forbs and grasses (AFG)
  - Perennial forbs and grasses (PFG)
  - Tree cover (TRE)

### Training Data
The model is trained on two types of labeled data:
- Manually annotated image chips (5000 chips, 19.2M hectares)
- Synthetic GLAD cropland extent samples (years 2003-2019)
    - (This synthetic GLAD data is the only data that is referenced in the rest of the github package)


### Usage
To use, please install the dependencies:
`pip install -r requirements.txt`

Then, you can train the model using the below. Change the yaml file to refer to specific data, learning rates, etc

```
python scripts/train.py \
    --config configs/train_config.yaml \
    --experiment EXPERIMENT_NAME \
    --run RUN_NAME
```


From there, run regional inference (either one year, or multiple years). 
If you are running regional inference on multiple years, you have to change the `batch_inference.sh` script as well. 
This script expects the following directory structure:

```
├── input_data/
│ ├── YYYY/ # Year-specific folders
│ │ ├── chunk_001.tfrecord
│ │ ├── chunk_001_mixer.json
│ │ ├── chunk_002.tfrecord
│ │ └── chunk_002_mixer.json
```

```
# single year
python scripts/inference.py \
    --config configs/inference_config.yaml \
    --experiment EXPERIMENT_NAME \
    --run YEAR

# Run batch inference for multiple years
./scripts/batch_inference.sh 1996 2021
```


Notes:
- Input data should be organized by year (YYYY)
- Each year folder contains TFRecord files split into chunks
- Each TFRecord chunk has an associated mixer JSON file
- Model outputs will be saved in a similar structure by year

