"""
AI Module for Civic Issue Reporting System.
Provides AI-generated image authenticity detection (Fake vs Real) using EfficientNetB7.
"""

from backend.app.ai.model import load_model, get_model, get_pipeline
from backend.app.ai.predict import predict_image

__all__ = ["load_model", "get_model", "get_pipeline", "predict_image"]
