"""
Data loading utilities for the Cropland Attention U-Net model.

This module handles all data loading operations including:
- TFRecord parsing and processing
- Dataset creation for training, evaluation, and inference
- Data partitioning for regional inference
"""

import tensorflow as tf
from typing import Dict, List, Tuple, Any
import glob

def parse_tfrecord(example_proto: tf.train.Example,
                   features_dict: Dict[str, Any]) -> Dict[str, tf.Tensor]:
    """Parse TFRecord example using provided feature dictionary.
    
    Args:
        example_proto: Serialized TFRecord example
        features_dict: Dictionary defining the TFRecord structure
        
    Returns:
        Dictionary of parsed tensors
    """
    return tf.io.parse_single_example(example_proto, features_dict)

def to_tuple(inputs: Dict[str, tf.Tensor],
            features: List[str],
            include_response: bool) -> Tuple[tf.Tensor, tf.Tensor]:
    """Convert dictionary of tensors to (input, output) tuple."""
    # Stack input features
    inputsList = [inputs.get(key) for key in features]
    stacked = tf.stack(inputsList, axis=0)
    # Convert from CHW to HWC
    stacked = tf.transpose(stacked, [1, 2, 0])
    
    if include_response:
        # Get response separately
        response = inputs.get('response_ag')
        response = tf.expand_dims(response, axis=-1)  # Add channel dimension
        return stacked, response
    return stacked, None

def get_dataset(pattern: str,
                features_dict: Dict[str, Any],
                features: List[str],
                include_response: bool = True) -> tf.data.Dataset:
    """Create dataset from TFRecord files.
    
    Args:
        pattern: Glob pattern for input files
        features_dict: Feature dictionary for parsing
        features: List of feature names
        include_response: Whether to include response variable
        
    Returns:
        TensorFlow dataset
    """
    files = tf.io.gfile.glob(pattern)
    dataset = tf.data.TFRecordDataset(files)
    
    # Partial functions to avoid passing constants
    parse_fn = lambda x: parse_tfrecord(x, features_dict)
    to_tuple_fn = lambda x: to_tuple(x, features, include_response)
    
    dataset = dataset.map(parse_fn, num_parallel_calls=5)
    dataset = dataset.map(to_tuple_fn, num_parallel_calls=5)
    return dataset

def get_dataset_gz(pattern: str,
                   features_dict: Dict[str, Any],
                   features: List[str],
                   include_response: bool = True) -> tf.data.Dataset:
    """Create dataset from compressed TFRecord files."""
    files = tf.io.gfile.glob(pattern)
    print(f"Reading {len(files)} compressed files")
    dataset = tf.data.TFRecordDataset(files, compression_type='GZIP')
    
    parse_fn = lambda x: parse_tfrecord(x, features_dict)
    to_tuple_fn = lambda x: to_tuple(x, features, include_response)
    
    dataset = dataset.map(parse_fn, num_parallel_calls=5)
    dataset = dataset.map(to_tuple_fn, num_parallel_calls=5)
    return dataset

def get_training_dataset(pattern: str,
                        features_dict: Dict[str, Any],
                        features: List[str],
                        buffer_size: int = 200,
                        batch_size: int = 16,
                        compressed: bool = False) -> tf.data.Dataset:
    """Get preprocessed training dataset."""
    dataset_fn = get_dataset_gz if compressed else get_dataset
    dataset = dataset_fn(pattern, features_dict, features)
    return dataset.shuffle(buffer_size).batch(batch_size).repeat()

def get_eval_dataset(pattern: str,
                     features_dict: Dict[str, Any],
                     features: List[str],
                     compressed: bool = False) -> tf.data.Dataset:
    """Get preprocessed evaluation dataset."""
    dataset_fn = get_dataset_gz if compressed else get_dataset
    dataset = dataset_fn(pattern, features_dict, features)
    return dataset.batch(1).repeat()

def get_regional_dataset(pattern: str,
                        features_dict: Dict[str, Any],
                        features: List[str],
                        compressed: bool = False) -> tf.data.Dataset:
    """Get dataset for regional inference."""
    dataset_fn = get_dataset_gz if compressed else get_dataset
    dataset = dataset_fn(pattern, features_dict, features)
    return dataset.batch(1)


def partition_record_files(data_list: List[str]) -> List[List[str]]:
    """Partition files into groups by chunk number."""
    file_groups = {}
    
    for path in data_list:
        components = path.split('_')
        chunk_number = components[components.index('chunk')+1]
        
        if chunk_number not in file_groups:
            file_groups[chunk_number] = []
        file_groups[chunk_number].append(path)
    
    return list(file_groups.values())