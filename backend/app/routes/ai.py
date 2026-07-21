import logging
from typing import Dict, Any

from fastapi import APIRouter, File, UploadFile, HTTPException, status
from fastapi.responses import JSONResponse

from backend.app.ai.predict import predict_image

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["AI Classifier"])

# Allowed image MIME types and extensions
ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/bmp",
    "image/tiff",
}

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}


@router.post("/predict", summary="Detect if an image is Fake (AI Generated) or Real")
async def predict_endpoint(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Accept an uploaded image file and detect whether it is Fake (AI Generated) or Real.

    Returns:
    - **prediction**: "Fake" or "Real"
    - **confidence**: Confidence percentage rounded to 2 decimal places (e.g. 98.41)
    - **probability**: Confidence score as a decimal float (e.g. 0.9841)
    """
    if not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file was uploaded.",
        )

    # File extension validation
    filename = file.filename or ""
    file_ext = ""
    if "." in filename:
        file_ext = "." + filename.rsplit(".", 1)[-1].lower()

    if file.content_type and file.content_type.lower() not in ALLOWED_MIME_TYPES:
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type '{file.content_type or file_ext}'. Allowed types: JPEG, PNG, WebP, BMP, TIFF.",
            )

    try:
        # Read uploaded image bytes
        contents = await file.read()
        if not contents:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty.",
            )

        # Perform inference
        result = predict_image(contents)
        return result

    except ValueError as val_err:
        logger.warning(f"Image validation failed: {val_err}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        )
    except Exception as exc:
        logger.error(f"Inference pipeline error: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI model inference failed: {str(exc)}",
        )
