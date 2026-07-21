import os
import logging
from pathlib import Path
from typing import Optional

import torch
import torch.nn as nn
import torchvision.models as models

logger = logging.getLogger(__name__)

# Global singletons for loaded model and execution device
_model: Optional[nn.Module] = None
_device: Optional[torch.device] = None

# Project root directory
PROJECT_ROOT = Path(__file__).resolve().parents[3]


def build_resnet50_model() -> nn.Module:
    """
    Construct ResNet50 model architecture matching the fine-tuned training config:
    - Base: torchvision.models.resnet50(weights=None)
    - Custom FC Head:
        Linear(2048, 512) -> BatchNorm1d(512) -> ReLU -> Dropout(0.4) ->
        Linear(512, 128) -> ReLU -> Dropout(0.3) -> Linear(128, 1)
    """
    model = models.resnet50(weights=None)
    num_features = model.fc.in_features  # 2048

    model.fc = nn.Sequential(
        nn.Linear(num_features, 512),
        nn.BatchNorm1d(512),
        nn.ReLU(),
        nn.Dropout(0.4),
        nn.Linear(512, 128),
        nn.ReLU(),
        nn.Dropout(0.3),
        nn.Linear(128, 1)
    )
    return model


def find_weights_file() -> Path:
    """Look for best_resnet50_finetuned.pth in candidate locations."""
    candidates = [
        PROJECT_ROOT / "AI" / "Models" / "best_resnet50_finetuned.pth",
        PROJECT_ROOT / "backend" / "app" / "models" / "best_resnet50_finetuned.pth",
        PROJECT_ROOT / "backend" / "models" / "best_resnet50_finetuned.pth",
        PROJECT_ROOT / "models" / "best_resnet50_finetuned.pth",
    ]

    for path in candidates:
        if path.exists():
            return path

    raise FileNotFoundError(
        f"Model weights file 'best_resnet50_finetuned.pth' not found in any of: "
        f"{[str(p) for p in candidates]}"
    )


def load_model() -> nn.Module:
    """
    Load the trained ResNet50 PyTorch model into memory (singleton pattern).
    Uses GPU (CUDA) if available, otherwise CPU.
    Sets model to evaluation mode.
    """
    global _model, _device

    if _model is not None:
        return _model

    # Determine execution device (GPU vs CPU)
    _device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Loading AI model onto device: {_device}")

    # Build model architecture
    model = build_resnet50_model()

    # Find weights file
    weights_path = find_weights_file()
    logger.info(f"Loading state_dict from: {weights_path}")

    # Load weights (state_dict)
    state_dict = torch.load(weights_path, map_location=_device)
    
    # Handle both direct state_dict and checkpoint dictionary formats
    if isinstance(state_dict, dict) and "state_dict" in state_dict:
        state_dict = state_dict["state_dict"]
    elif isinstance(state_dict, dict) and "model_state_dict" in state_dict:
        state_dict = state_dict["model_state_dict"]

    model.load_state_dict(state_dict)
    model.to(_device)
    model.eval()

    _model = model
    logger.info("AI model loaded successfully and set to eval mode.")
    return _model


def get_model() -> nn.Module:
    """Return the loaded model instance. Loads it lazily if not already loaded."""
    if _model is None:
        return load_model()
    return _model


def get_device() -> torch.device:
    """Return the current PyTorch device (cuda/cpu)."""
    global _device
    if _device is None:
        _device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return _device
