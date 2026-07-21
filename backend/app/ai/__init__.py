"""
AI Module for Civic Issue Reporting System.
Provides AI-generated image detection (Fake vs Real).
"""

from backend.app.ai.model import load_model, get_model, get_device
from backend.app.ai.predict import predict_image

__all__ = ["load_model", "get_model", "get_device", "predict_image"]
