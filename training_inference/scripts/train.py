"""
Training script for the Cropland Attention U-Net model.

This script allows users to implements a multi-stage training process for cropland segmentation.
For each step, change `configs/train_config.yaml` and point to specific data sources.

The processed used for the Annual Cropland Extent product is below:

	1. Pre-training (GLAD data only):
   		- Initial training for 25 epochs using synthetic GLAD labels
   		- Learning rate: 0.0001
   		- All layers trainable
   		- Purpose: Learn general cropland features across broad spatial extent

	2. Encoder Freezing (GLAD data):
   		- Additional 50 epochs with frozen encoder weights
   		- Learning rate: 0.001 with decay
   		- Only decoder layers trainable
   		- Purpose: Leverage pre-trained features while preventing overfitting

	3. Fine-tuning (Chip data):
   		- 50 epochs using manually annotated chip dataset
   		- Learning rate: 0.001 with decay
   		- Encoder remains frozen, decoder trainable
   		- Purpose: Adapt to regional variations and complex landscapes

	4. Full Training (Chip data):
   		- 100 epochs using chip dataset
   		- Learning rate: 0.005 with decay
   		- All layers unfrozen
   		- Purpose: Final optimization across all parameters

The model uses the Adam optimizer and Focal Tversky loss function to handle
class imbalance and minimize false positives in segmentation.

Usage:
    python train.py --config configs/train_config.yaml --experiment EXP_NAME --run RUN_NAME

Arguments:
    --config: Path to training configuration YAML file
    --experiment: Name of experiment for wandb logging
    --run: Specific run name within the experiment
"""


import argparse
import wandb
import tensorflow as tf
import keras
import os
from keras_unet_collection import models
from keras_unet_collection.losses import focal_tversky
from pathlib import Path

# Local imports
from src.config import TrainingConfig
from src.data_loading import get_training_dataset, get_eval_dataset
from src.model_utils import dice_loss, dice_coef

def setup_gpu_memory():
    """Configure GPU memory settings."""
    gpus = tf.config.list_physical_devices('GPU')
    if gpus:
        try:
            tf.config.set_logical_device_configuration(
                gpus[0],
                [tf.config.LogicalDeviceConfiguration(memory_limit=25000)])
            logical_gpus = tf.config.list_logical_devices('GPU')
            print(f"{len(gpus)} Physical GPUs, {len(logical_gpus)} Logical GPUs")
        except RuntimeError as e:
            print(e)

def create_model(n_channels: int):
    """Create Attention U-Net model."""
    return models.att_unet_2d(
        (None, None, n_channels), 
        filter_num=[32, 64, 128, 256, 512],
        n_labels=1,
        stack_num_down=2,
        stack_num_up=2,
        activation='ReLU',
        atten_activation='ReLU',
        attention='add',
        output_activation='Sigmoid',
        batch_norm=True,
        pool=False,
        unpool=False,
        backbone=None,
        weights=None,
        freeze_backbone=False,
        freeze_batch_norm=False,
        name='attunet'
    )

def freeze_backbone(model, strategy: str):
    """Apply backbone freezing strategy."""
    if strategy == "none":
        return
    
    elif strategy == "full":
        for layer in model.layers:
            if 'down' in layer.name and ('encode_stride_conv' in layer.name or 'conv' in layer.name):
                if not isinstance(layer, tf.keras.layers.BatchNormalization):
                    layer.trainable = False
                    
    

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, required=True)
    parser.add_argument("--experiment", type=str, required=True)
    parser.add_argument("--run", type=str, required=True)
    args = parser.parse_args()

    # Load configuration
    config = TrainingConfig(args.config)
    
    # Setup GPU memory
    setup_gpu_memory()
    
    # Prepare data
    data_path = Path(config.get_paths()['data_folder'])
    train_pattern = str(data_path / config.get_paths()['train_base'] / "*.tfrecord")
    eval_pattern = str(data_path / config.get_paths()['eval_base'] / "*.tfrecord")
    
    training = get_training_dataset(
        pattern=train_pattern,
        features_dict=config.get_features_dict(),
        features=config.input_bands,
        batch_size=config.batch_size,
        compressed=config.is_compressed
    )

    evaluation = get_eval_dataset(
        pattern=eval_pattern,
        features_dict=config.get_features_dict(),
        features=config.input_bands,
        compressed=config.is_compressed
    )
    print('Data loaded successfully')
    
    # Initialize or load model
    if config.use_pretrained:
        print('Loading pre-trained model')
        model = keras.models.load_model(config.pretrained_model_path, compile=False)
    else:
        print('Creating new model')
        model = create_model(len(config.input_bands))
    
    # Apply freezing strategy
    freeze_backbone(model, config.backbone_freeze)
    print("Model prepared successfully")
    
    # Initialize wandb
    wandb.init(
        project=args.experiment,
        config={
            "batch_size": config.batch_size,
            "learning_rate": config.learning_rate,
            "dataset": "Mexico-Training",
            "run": args.run,
            "epochs": config.epochs,
        }
    )
    
    # Setup callbacks
    callbacks = [
        tf.keras.callbacks.ModelCheckpoint(
            os.path.join(args.experiment, args.run, 'bestEpoch.h5'),
            monitor='val_mean_io_u',
            save_best_only=True,
            mode='max'
        ),
        tf.keras.callbacks.ModelCheckpoint(
            os.path.join(args.experiment, args.run, 'lastEpoch.h5')
        ),
        wandb.keras.WandbCallback(log_weights=True)
    ]
    
    # Configure optimizer
    optimizer = tf.keras.optimizers.Adamax(
        learning_rate=config.learning_rate,
        beta_1=0.9,
        beta_2=0.999,
        epsilon=1e-07,
    )
    
    # Compile model
    loss_fn = focal_tversky if config.loss_function == "focal_tversky" else dice_loss
    model.compile(
        optimizer=optimizer,
        loss=loss_fn,
        metrics=[
            tf.keras.metrics.MeanIoU(num_classes=2),
            dice_coef,
            'accuracy'
        ],
        run_eagerly=True
    )
    
    # Train model
    print("Starting model training")
    model.fit(
        x=training,
        epochs=config.epochs,
        steps_per_epoch=int(config.train_size / config.batch_size),
        validation_data=evaluation,
        validation_steps=config.eval_size,
        callbacks=callbacks
    )

if __name__ == "__main__":
    main()
