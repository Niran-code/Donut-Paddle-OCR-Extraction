# Document OCR Extraction API

This repository contains an optimized CPU-first AI OCR Extraction Pipeline for Indian Identity Documents.

The architecture uses a Hybrid Pipeline (PaddleOCR Regex Heuristics + Donut Fallback) to process identity documents asynchronously via a Celery worker setup or synchronously via REST endpoints.

## Hardware Optimization
This repository currently ships with configurations strictly optimized for **CPU-only inference**:
- `enable_mkldnn=True` is active inside the PaddleOCR Engine, allowing for ~2 second extraction times on CPUs.
- If you intend to run this on a GPU instance, ensure you update `use_gpu=False` to `True` in `pipeline/ocr_engine.py` and install the `paddlepaddle-gpu` libraries.

---

## 🚀 Setup Instructions for DevOps

### 1. Requirements & Dependencies
Ensure you have Python 3.10+ installed.

```bash
# Set up virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Redis Setup (Message Broker)
The asynchronous architecture requires Redis to handle Celery tasks.
Make sure you have a Redis server running locally or update the `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` variables inside `run.py`.
```bash
# Example to run Redis via Docker
docker run -d -p 6379:6379 redis
```

### 3. Running the Microservices
The system relies on two separate processes to run correctly. You can configure `systemd` or `supervisord` to manage these processes in production.

**Process A: The Celery Worker (Background Inference Queue)**
```bash
# In your source directory, mapped to your venv
celery -A run.celery_app worker --loglevel=info
```

**Process B: The Flask API Server**
```bash
# In your source directory, mapped to your venv
# Runs on Port 5000 by default
python run.py
```
*(Optionally use `gunicorn -w 4 -b 0.0.0.0:5000 run:app` for a production WSGI setup).*

---

## 📡 API Endpoints 

### 1. `POST /process` (Synchronous)
Processes a `.jpg`, `.png`, or `.pdf` instantly on the main thread and returns the extracted JSON. Not recommended for high-volume or large PDFs as it blocks the request thread.
- **Form Data:** `file` -> `<Your Document Image/PDF>`

### 2. `POST /api/v1/process_async` (Asynchronous)
Uploads the image or PDF to the background Celery Queue and returns an immediate ID.
- **Form Data:** `file` -> `<Your Document Image/PDF>`
- **Response:** `{"task_id": "8487c958-8d3f-405f-b3bd-3a4f9a57bb16", "status": "Processing Started"}`

### 3. `GET /api/v1/status/<task_id>`
Poll this endpoint using the UUID returned from the asynchronous route to retrieve the extraction result once the state transitions from `PROCESSING` to `SUCCESS`.

---

## Folders
- `app/` - Flask API and Celery Queue Configurations.
- `pipeline/` - Core extraction logic, regex scripts (`cleaner.py`), schemas, and Model loaders.
- `uploads/` - Temporarily stores incoming file requests.
- `dataset/` - Directory originally used for holding custom testing samples. Can be safely ignored or deleted.
