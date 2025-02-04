import yaml
import tensorflow as tf
from typing import Dict, Any, List
from pathlib import Path

class Config:
    def __init__(self, config_path: str):
        """Initialize configuration from YAML file.
        
        Args:
            config_path: Path to YAML configuration file
        """
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
            
    @property
    def input_bands(self) -> List[str]:
        """Get list of input bands."""
        return self.config['data']['input_bands']
    
    @property
    def include_response(self) -> bool:
        """Whether to include response variable."""
        return self.config['data']['include_response']
    
    @property
    def kernel_size(self) -> int:
        """Get kernel size for image patches."""
        return self.config['data']['kernel_size']
    
    @property
    def is_compressed(self) -> bool:
        """Whether TFRecords are compressed."""
        return self.config['data']['compressed']
    
    @property
    def kernel_shape(self) -> List[int]:
        """Get kernel shape for TFRecord parsing."""
        return [self.kernel_size, self.kernel_size]

    def get_features_dict(self) -> Dict[str, Any]:
        """Get feature dictionary for TFRecord parsing."""
        features = self.input_bands.copy()
        if self.include_response:
            features.append('response_ag')
        
        columns = [
            tf.io.FixedLenFeature(shape=self.kernel_shape, 
                                 dtype=tf.float32) 
            for _ in features
        ]
        return dict(zip(features, columns))
    
    def get_paths(self) -> Dict[str, str]:
        """Get all relevant paths from config."""
        return self.config['paths']
    
    def get_training_params(self) -> Dict[str, Any]:
        """Get training parameters if present."""
        return self.config.get('training', {})
    
    def get_inference_params(self) -> Dict[str, Any]:
        """Get inference parameters if present."""
        return self.config.get('inference', {})

class TrainingConfig(Config):
    """Training-specific configuration."""
    
    @property
    def train_size(self) -> int:
        return self.config['data']['train_size']
    
    @property
    def eval_size(self) -> int:
        return self.config['data']['eval_size']
    
    @property
    def batch_size(self) -> int:
        return self.config['training']['batch_size']
    
    @property
    def learning_rate(self) -> float:
        return self.config['training']['learning_rate']
    
    @property
    def epochs(self) -> int:
        return self.config['training']['epochs']
    
    @property
    def backbone_freeze(self) -> str:
        return self.config['training']['backbone_freeze']['strategy']
    
    @property
    def loss_function(self) -> str:
        return self.config['training']['loss_function']

    @property
    def use_pretrained(self) -> bool:
        """Whether to use a pre-trained model."""
        return self.config['training']['existing_model']['use_pretrained']
    
    @property
    def pretrained_model_path(self) -> str:
        """Get path to pre-trained model if using one."""
        if not self.use_pretrained:
            return None
        return self.config['training']['existing_model']['model_path']

class InferenceConfig(Config):
    """Inference-specific configuration."""
    
    @property
    def batch_size(self) -> int:
        return self.config['inference']['batch_size']
    
    @property
    def memory_limit(self) -> int:
        return self.config['inference']['memory_limit']
    
    @property
    def exclude_chunks(self) -> List[int]:
        return self.config['inference']['exclude_chunks']
