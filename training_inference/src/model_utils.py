"""
Model utilities for the Cropland Attention U-Net model.

This module contains loss functions, metrics, and other model-related utilities
used in training and evaluating the segmentation model.
"""

import tensorflow as tf
import tensorflow.keras.backend as K
from typing import Any

def dice_coef(y_true: tf.Tensor, 
              y_pred: tf.Tensor, 
              const: float = K.epsilon()) -> tf.Tensor:
    """Calculate Sørensen–Dice coefficient for 2-d samples.

    Args:
        y_true: Ground truth values
        y_pred: Predicted values
        const: Smoothing constant for numerical stability

    Returns:
        Dice coefficient value
    """
    # Flatten 2-d tensors
    y_true_pos = tf.reshape(y_true, [-1])
    y_pred_pos = tf.reshape(y_pred, [-1])

    # Get true pos (TP), false neg (FN), false pos (FP)
    true_pos = tf.reduce_sum(y_true_pos * y_pred_pos)
    false_neg = tf.reduce_sum(y_true_pos * (1-y_pred_pos))
    false_pos = tf.reduce_sum((1-y_true_pos) * y_pred_pos)

    # Calculate coefficient
    coef_val = (2.0 * true_pos + const)/(2.0 * true_pos + false_pos + false_neg)
    return coef_val

def dice_loss(y_true: tf.Tensor, 
              y_pred: tf.Tensor, 
              const: float = K.epsilon()) -> tf.Tensor:
    """Calculate Sørensen–Dice loss for 2-d samples.

    Args:
        y_true: Ground truth values
        y_pred: Predicted values
        const: Smoothing constant for numerical stability

    Returns:
        Dice loss value
    """
    return 1 - dice_coef(y_true, y_pred, const)

def compute_iou(y_true: tf.Tensor, 
                y_pred: tf.Tensor) -> tf.Tensor:
    """Compute Intersection over Union (IoU) metric.

    Args:
        y_true: Ground truth values
        y_pred: Predicted values

    Returns:
        IoU value
    """
    # Flatten 2-d tensors
    y_true = tf.reshape(y_true, [-1])
    y_pred = tf.reshape(y_pred, [-1])

    # Ensure prediction is binary
    y_pred = tf.round(y_pred)

    # Compute intersection and union
    intersection = tf.reduce_sum(y_true * y_pred)
    union = tf.reduce_sum(y_true) + tf.reduce_sum(y_pred) - intersection

    # Avoid division by zero
    iou = tf.where(tf.equal(union, 0), 1., intersection / union)
    return iou

def iou_loss(y_true: tf.Tensor, 
             y_pred: tf.Tensor) -> tf.Tensor:
    """Compute IoU loss.

    Args:
        y_true: Ground truth values
        y_pred: Predicted values

    Returns:
        IoU loss value
    """
    return 1 - compute_iou(y_true, y_pred)