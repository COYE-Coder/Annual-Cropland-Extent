#!/bin/bash

# Batch inference script for running regional predictions across multiple years
# Usage: ./batch_inference.sh <start_year> <end_year>

start_year=${1:-1996}  # Default to 2005 if not provided
end_year=${2:-2021}    # Default to 2021 if not provided

# Configuration
experiment="AG_INFERENCE"
existing_model="/path/to/your/wandb/experiment/bestEpoch.h5"
gcloud_output="gs://path/to/your/gcloud/bucket/model_output"

echo "Starting batch inference for years $start_year to $end_year"
echo "Using model: $existing_model"
echo "Saving outputs to: $gcloud_output"

for ((year=start_year; year<=end_year; year++))
do
    echo "Processing year $year..."
    input_folder="/path/to/input/data/folder/${year}/"
    run_output="${gcloud_output}/${year}"
    
    python3 scripts/inference.py \
        --config configs/inference_config.yaml \
        --experiment ${experiment} \
        --run ${year}
        
    if [ $? -ne 0 ]; then
        echo "Error processing year $year"
        exit 1
    fi
    
    echo "Completed year $year"
done

echo "Batch inference complete"