import io

import numpy as np
from fastapi.testclient import TestClient
from PIL import Image

from app.preprocessing.image_ops import resize_image
from app.services.pipeline import run_pipeline
from app.main import app


def png_bytes(width=80, height=40):
    image = Image.new("RGB", (width, height), "white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def jpeg_bytes():
    image = Image.new("RGB", (80, 40), "white")
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    return buffer.getvalue()


def test_homepage():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "Process" in response.text
    assert "Copy text" in response.text
    assert "Download text" in response.text


def test_recognize_png(monkeypatch, tmp_path):
    monkeypatch.setenv("RESULT_DIR", str(tmp_path))
    monkeypatch.setattr(
        "app.recognition.ocr.pytesseract.image_to_string",
        lambda image, lang="eng", config="": "Hello",
    )
    client = TestClient(app)
    response = client.post(
        "/api/recognize",
        files={"file": ("note.png", png_bytes(), "image/png")},
    )
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["text"], str)
    assert isinstance(body["processing_ms"], (int, float))
    assert body["filename"] == "note.png"
    downloaded = client.get(f"/api/results/{body['id']}/download")
    assert downloaded.status_code == 200
    assert downloaded.text == "Hello"


def test_pipeline_sends_preprocessed_image_to_ocr(monkeypatch):
    received = {}

    def capture_image(image, config):
        received["image"] = image
        return "Hello"

    monkeypatch.setattr("app.services.pipeline.extract_text", capture_image)
    run_pipeline(png_bytes())
    assert received["image"].ndim == 2


def test_resize_image_preserves_aspect_ratio():
    image = np.zeros((280, 1400, 3), dtype=np.uint8)
    resized = resize_image(image)
    assert resized.shape[:2] == (160, 800)


def test_recognize_jpeg(monkeypatch, tmp_path):
    monkeypatch.setenv("RESULT_DIR", str(tmp_path))
    monkeypatch.setattr(
        "app.recognition.ocr.pytesseract.image_to_string",
        lambda image, lang="eng", config="": "Hello",
    )
    client = TestClient(app)
    response = client.post(
        "/api/recognize",
        files={"file": ("scan.jpg", jpeg_bytes(), "image/jpeg")},
    )
    assert response.status_code == 200
    assert isinstance(response.json()["text"], str)


def test_missing_file():
    client = TestClient(app)
    response = client.post("/api/recognize")
    assert response.status_code == 422


def test_rejects_pdf():
    client = TestClient(app)
    response = client.post(
        "/api/recognize",
        files={"file": ("notes.pdf", b"%PDF-1.4", "application/pdf")},
    )
    assert response.status_code == 400


def test_rejects_png_with_wrong_content():
    client = TestClient(app)
    response = client.post(
        "/api/recognize",
        files={"file": ("note.png", b"not-an-image", "image/png")},
    )
    assert response.status_code == 400


def test_rejects_oversized_image():
    client = TestClient(app)
    payload = png_bytes() + b"0" * (5 * 1024 * 1024)
    response = client.post(
        "/api/recognize",
        files={"file": ("large.png", payload, "image/png")},
    )
    assert response.status_code == 400


def test_rejects_path_filename(monkeypatch, tmp_path):
    monkeypatch.setenv("RESULT_DIR", str(tmp_path))
    client = TestClient(app)
    response = client.post(
        "/api/recognize",
        files={"file": ("../../secret.png", png_bytes(), "image/png")},
    )
    assert response.status_code == 400
