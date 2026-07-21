import io
from PIL import Image
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def create_dummy_image_bytes(color=(255, 0, 0), format="JPEG") -> bytes:
    """Create a dummy 224x224 RGB image in memory and return bytes."""
    img = Image.new("RGB", (224, 224), color=color)
    buf = io.BytesIO()
    img.save(buf, format=format)
    return buf.getvalue()


def test_predict_endpoint_success():
    """Test POST /api/ai/predict with a valid JPEG image."""
    img_bytes = create_dummy_image_bytes(color=(100, 150, 200), format="JPEG")
    response = client.post(
        "/api/ai/predict",
        files={"file": ("test.jpg", img_bytes, "image/jpeg")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "prediction" in data
    assert data["prediction"] in ["Fake", "Real"]
    assert "confidence" in data
    assert isinstance(data["confidence"], (int, float))
    assert 0 <= data["confidence"] <= 100
    assert "probability" in data
    assert isinstance(data["probability"], (int, float))
    assert 0 <= data["probability"] <= 1.0


def test_predict_endpoint_alias():
    """Test POST /api/predict alias endpoint."""
    img_bytes = create_dummy_image_bytes(color=(50, 50, 50), format="PNG")
    response = client.post(
        "/api/predict",
        files={"file": ("test.png", img_bytes, "image/png")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "prediction" in data
    assert data["prediction"] in ["Fake", "Real"]


def test_predict_invalid_file_type():
    """Test POST /api/ai/predict with a text file (should return 400)."""
    response = client.post(
        "/api/ai/predict",
        files={"file": ("test.txt", b"Hello world", "text/plain")},
    )
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_predict_corrupted_image():
    """Test POST /api/ai/predict with corrupted image bytes (should return 400)."""
    response = client.post(
        "/api/ai/predict",
        files={"file": ("corrupt.jpg", b"NOT_AN_IMAGE_DATA", "image/jpeg")},
    )
    assert response.status_code == 400
    assert "Invalid or corrupted image" in response.json()["detail"]
