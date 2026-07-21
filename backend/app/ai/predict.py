import io
import logging
from typing import Dict, Any, Union

from PIL import Image, ImageOps
import torch
import torchvision.transforms as transforms

from backend.app.ai.model import get_model, get_device

logger = logging.getLogger(__name__)

# ImageNet standard normalization statistics used during training
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]

# Preprocessing pipeline matching training configuration
inference_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
])


def preprocess_image(image_input: Union[Image.Image, bytes, io.BytesIO]) -> torch.Tensor:
    """
    Load and preprocess an image for model inference:
    1. Convert bytes/stream to PIL Image if needed
    2. Convert mode to RGB (handles RGBA, Grayscale, palette images)
    3. Apply EXIF orientation fix if needed
    4. Resize to 224x224, convert to Tensor, and normalize with ImageNet stats
    5. Add batch dimension (1, C, H, W)
    """
    try:
        if isinstance(image_input, (bytes, bytearray)):
            image = Image.open(io.BytesIO(image_input))
        elif isinstance(image_input, io.BytesIO):
            image = Image.open(image_input)
        elif isinstance(image_input, Image.Image):
            image = image_input
        else:
            raise ValueError(f"Unsupported image input type: {type(image_input)}")

        # Fix EXIF orientation if present
        image = ImageOps.exif_transpose(image)

        # Convert to RGB (3 channels)
        if image.mode != "RGB":
            image = image.convert("RGB")

        # Apply torchvision transforms
        tensor = inference_transform(image)  # Shape: (3, 224, 224)

        # Add batch dimension: (1, 3, 224, 224)
        tensor = tensor.unsqueeze(0)
        return tensor

    except Exception as e:
        logger.error(f"Failed to preprocess image: {e}")
        raise ValueError(f"Invalid or corrupted image: {str(e)}")


def predict_image(image_input: Union[Image.Image, bytes, io.BytesIO]) -> Dict[str, Any]:
    """
    Run AI inference on an image to detect if it is Fake (AI Generated) or Real.

    Returns dict matching requested schema:
    {
        "prediction": "Fake" | "Real",
        "confidence": 98.41,
        "probability": 0.9841
    }
    """
    # Preprocess image into tensor
    input_tensor = preprocess_image(image_input)

    # Get singleton model and device
    model = get_model()
    device = get_device()

    input_tensor = input_tensor.to(device)

    # Perform forward pass in no_grad mode
    with torch.no_grad():
        logits = model(input_tensor)
        # Apply sigmoid to convert logit to probability of class 1 (Real)
        real_prob = torch.sigmoid(logits).item()

    # Decision threshold = 0.5
    # Class 0 = Fake (AI Generated)
    # Class 1 = Real
    if real_prob > 0.5:
        prediction = "Real"
        class_probability = real_prob
    else:
        prediction = "Fake"
        class_probability = 1.0 - real_prob

    # Round confidence to 2 decimal places and probability to 4 decimal places
    confidence = round(class_probability * 100.0, 2)
    probability = round(class_probability, 4)

    result = {
        "prediction": prediction,
        "confidence": confidence,
        "probability": probability,
    }

    logger.info(
        f"Inference result: prediction={prediction}, "
        f"confidence={confidence}%, probability={probability}"
    )

    return result
