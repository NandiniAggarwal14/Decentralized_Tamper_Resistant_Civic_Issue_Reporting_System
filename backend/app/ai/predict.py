import io
import logging
from typing import Dict, Any, Union
from PIL import Image, ImageOps

from backend.app.ai.model import get_pipeline

logger = logging.getLogger(__name__)

def preprocess_image(image_input: Union[Image.Image, bytes, io.BytesIO]) -> Image.Image:
    """Load bytes or stream into RGB PIL Image with EXIF transpose."""
    try:
        if isinstance(image_input, (bytes, bytearray)):
            image = Image.open(io.BytesIO(image_input))
        elif isinstance(image_input, io.BytesIO):
            image = Image.open(image_input)
        elif isinstance(image_input, Image.Image):
            image = image_input
        else:
            raise ValueError(f"Unsupported image input type: {type(image_input)}")

        image = ImageOps.exif_transpose(image)
        if image.mode != "RGB":
            image = image.convert("RGB")
        return image
    except Exception as e:
        logger.error(f"Failed to preprocess image for AI inference: {e}")
        raise ValueError(f"Invalid or corrupted image: {str(e)}")

def predict_image(image_input: Union[Image.Image, bytes, io.BytesIO]) -> Dict[str, Any]:
    """
    Run EfficientNetB7 deepfake classification on an image.
    Returns:
    {
        "prediction": "Fake" | "Real",
        "confidence": 98.41,
        "probability": 0.9841
    }
    """
    image = preprocess_image(image_input)
    pipe = get_pipeline()

    if pipe is None:
        logger.warning("AI model pipeline not loaded. Returning neutral fallback.")
        return {
            "prediction": "Real",
            "confidence": 50.0,
            "probability": 0.50
        }

    try:
        preds = pipe(image)
        # HuggingFace pipeline returns list of dicts: [{'label': 'FAKE', 'score': 0.9841}, ...]
        top = preds[0]
        raw_label = str(top.get("label", "REAL")).upper()
        raw_score = float(top.get("score", 0.5))

        if "FAKE" in raw_label or "SYNTHETIC" in raw_label or "LABEL_1" in raw_label:
            prediction = "Fake"
        else:
            prediction = "Real"

        confidence = round(raw_score * 100.0, 2)
        probability = round(raw_score, 4)

        result = {
            "prediction": prediction,
            "confidence": confidence,
            "probability": probability,
        }

        logger.info(f"AI EfficientNetB7 prediction: prediction={prediction}, confidence={confidence}%")
        return result

    except Exception as exc:
        logger.error(f"Error during AI pipeline inference: {exc}")
        return {
            "prediction": "Real",
            "confidence": 50.0,
            "probability": 0.50
        }
