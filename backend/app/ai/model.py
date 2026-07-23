import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)

# Global singleton for loaded HuggingFace classification pipeline
_pipeline: Optional[Any] = None

def load_model() -> Any:
    """
    Load the HuggingFace EfficientNetB7 deepfake detection model pipeline into memory (singleton).
    Model ID: dima806/deepfake_vs_real_image_detection
    """
    global _pipeline

    if _pipeline is not None:
        return _pipeline

    logger.info("Loading HuggingFace EfficientNetB7 Deepfake Detector 'dima806/deepfake_vs_real_image_detection'...")
    try:
        from transformers import pipeline
        _pipeline = pipeline("image-classification", model="dima806/deepfake_vs_real_image_detection")
        logger.info("EfficientNetB7 Deepfake Classifier loaded successfully.")
    except Exception as exc:
        logger.error(f"Failed to load EfficientNetB7 pipeline: {exc}")
        _pipeline = None

    return _pipeline

def get_model() -> Any:
    """Return the loaded pipeline instance. Loads lazily if not already loaded."""
    if _pipeline is None:
        return load_model()
    return _pipeline

def get_pipeline() -> Any:
    """Alias for get_model()."""
    return get_model()
