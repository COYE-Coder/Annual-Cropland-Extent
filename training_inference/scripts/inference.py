"""
Regional inference script for the Cropland Attention U-Net model.

This script loads a trained model and runs inference on regional data, 
exporting predictions to Google Cloud Storage. The process includes:
1. Loading regional data in chunks to manage memory
2. Running model predictions on each chunk
3. Exporting predictions to GCS in TFRecord format
4. Copying associated mixer files to the same GCS location

Usage:
    python inference.py --config configs/inference_config.yaml --experiment EXP_NAME --run RUN_NAME

Arguments:
    --config: Path to inference configuration YAML file
    --experiment: Name of experiment for wandb logging
    --run: Specific run identifier
"""

import argparse
import wandb
import tensorflow as tf
import keras
import os
from pathlib import Path
import glob
import subprocess
from typing import List

# Local imports
from src.config import InferenceConfig
from src.data_loading import get_regional_dataset, partition_record_files

def setup_gpu_memory(memory_limit: int = 25000):
    """Configure GPU memory settings."""
    gpus = tf.config.list_physical_devices('GPU')
    if gpus:
        try:
            tf.config.set_logical_device_configuration(
                gpus[0],
                [tf.config.LogicalDeviceConfiguration(memory_limit=memory_limit)])
            logical_gpus = tf.config.list_logical_devices('GPU')
            print(f"{len(gpus)} Physical GPUs, {len(logical_gpus)} Logical GPUs")
        except RuntimeError as e:
            print(e)

def write_predictions(prediction_patches: tf.Tensor,
                     output_path: str) -> None:
    """Write prediction patches to TFRecord file."""
    writer = tf.io.TFRecordWriter(output_path)
    patches = 0
    
    for patch in prediction_patches:
        if patches % 1000 == 0:
            print(f'Writing patch {patches} to {output_path} ...')
            
        example = tf.train.Example(
            features=tf.train.Features(
                feature={
                    'response_ag': tf.train.Feature(
                        float_list=tf.train.FloatList(
                            value=patch.flatten()
                        )
                    )
                }
            )
        )
        writer.write(example.SerializeToString())
        patches += 1
        
    writer.close()

def copy_mixers_to_gcs(input_folder: str,
                      gcloud_output: str) -> None:
    """Copy mixer files to Google Cloud Storage."""
    print("Copying mixers to Google Cloud")
    eval_mixers = glob.glob(f'{input_folder}*.json')
    
    for json_file in eval_mixers:
        basename = os.path.basename(json_file)
        cmd = ['gsutil', 'cp', json_file, f'{gcloud_output}{basename}']
        subprocess.run(cmd)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, required=True)
    parser.add_argument("--experiment", type=str, required=True)
    parser.add_argument("--run", type=str, required=True)
    args = parser.parse_args()

    # Load configuration
    config = InferenceConfig(args.config)
    
    # Setup GPU memory
    setup_gpu_memory(config.memory_limit)
    
    # Initialize wandb
    wandb.init(
        project=args.experiment,
        config={
            "dataset": "Regional-Inference",
            "run": args.run
        }
    )
    
    # Load model
    model = keras.models.load_model(
        config.get_paths()['existing_model'],
        compile=False
    )
    print("Model loaded successfully")
    
    # Get input files and partition them
    input_folder = config.get_paths()['input_folder']
    eval_files = glob.glob(f'{input_folder}*.tfrecord')
    print(f"Found {len(eval_files)} files to process")
    
    partitioned_images = partition_record_files(eval_files)
    
    # Process each partition
    for image_list in partitioned_images:
        image_list.sort()
        file_name = Path(image_list[0]).stem
        print(f"Processing {file_name}")
        
        dataset = get_regional_dataset(
            image_list=image_list,
            features_dict=config.get_features_dict(),
            features=config.input_bands
        )
        predictions = model.predict(dataset, verbose=1)
        
        output_path = f"{config.get_paths()['gcloud_output']}{file_name}_pred.tfrecord"
        write_predictions(predictions, output_path)
    
    # Copy mixer files
    copy_mixers_to_gcs(
        input_folder=config.get_paths()['input_folder'],
        gcloud_output=config.get_paths()['gcloud_output']
    )

if __name__ == "__main__":
    main()