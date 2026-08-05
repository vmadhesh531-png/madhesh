# AI Image-to-Bill Module

Production-ready AI-powered bill extraction backend using Google Gemini 2.5 Flash.

## Features

- **Multi-format Support**: JPG, JPEG, PNG, PDF (up to 20MB)
- **Advanced Preprocessing**: Auto-rotate, denoise, sharpen, contrast enhancement, adaptive thresholding
- **AI Extraction**: Google Gemini Vision for accurate OCR and structured data extraction
- **Smart Validation**: Automatic calculation checks, duplicate detection, GST validation
- **Confidence Scoring**: Per-field confidence scores for reliability assessment
- **Async API**: FastAPI with async endpoints for high performance

## Quick Start

### 1. Setup Environment

```bash
# Clone and enter directory
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# For PDF support, install poppler (system dependency)
# Ubuntu/Debian: sudo apt-get install poppler-utils
# macOS: brew install poppler
# Windows: https://github.com/oschwartz10612/poppler-windows

# Configure environment
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

### 2. Run Application

```bash
# Development
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Production
uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4
```

### 3. API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/upload-image` | POST | Upload image/PDF |
| `/api/extract-bill` | POST | Extract bill data |
| `/api/validate` | POST | Re-validate extracted data |
| `/api/result/{id}` | GET | Get result by ID |
| `/api/health` | GET | Health check |

### 4. Example Usage

**Upload Image:**
```bash
curl -X POST "http://localhost:8000/api/upload-image" \
  -F "file=@receipt.jpg" \
  -F "preprocess=true"
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "receipt.jpg",
  "file_hash": "a1b2c3...",
  "status": "uploaded",
  "message": "Image uploaded successfully. Use /api/extract-bill to process."
}
```

**Extract Bill:**
```bash
curl -X POST "http://localhost:8000/api/extract-bill" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "preprocess": true
  }'
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "bill_data": {
    "store_name": "SuperMart",
    "invoice_number": "INV-001234",
    "invoice_date": "2024-01-15",
    "invoice_time": "14:30",
    "gst_number": "27AABCU9603R1ZM",
    "address": "123 Main Street, Mumbai",
    "currency": "INR",
    "payment_method": "UPI",
    "subtotal": 950.00,
    "discount": 50.00,
    "tax": 108.00,
    "total": 1008.00,
    "items": [
      {
        "item_name": "Organic Rice 5kg",
        "quantity": 2,
        "unit_price": 250.00,
        "amount": 500.00
      },
      {
        "item_name": "Sunflower Oil 1L",
        "quantity": 3,
        "unit_price": 150.00,
        "amount": 450.00
      }
    ]
  },
  "confidence": {
    "store_name": 0.95,
    "invoice_number": 0.98,
    "total": 0.99,
    "items": 0.92
  },
  "validation": {
    "is_valid": true,
    "errors": [],
    "warnings": [],
    "duplicate_items": [],
    "calculation_errors": []
  },
  "created_at": "2024-01-15T10:30:00Z",
  "processed_at": "2024-01-15T10:30:05Z"
}
```

## Architecture

```
┌─────────────┐     ┌─────────────────┐     ┌──────────────┐
│   Upload    │────▶│  Preprocessing  │────▶│   Gemini     │
│   Image     │     │  (OpenCV/PIL)   │     │    Vision    │
└─────────────┘     └─────────────────┘     └──────────────┘
                                                    │
┌─────────────┐     ┌─────────────────┐            │
│   Return    │◀────│   Validation    │◀───────────┘
│    JSON     │     │   & Scoring     │
└─────────────┘     └─────────────────┘
```

## Configuration

All configuration via environment variables (`.env`):

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | *required* | Google Gemini API key |
| `GEMINI_MODEL` | gemini-2.5-flash-preview-05-20 | Model name |
| `MAX_UPLOAD_SIZE` | 20971520 | Max file size (bytes) |
| `LOG_LEVEL` | INFO | Logging level |

## Project Structure

```
backend/
├── app/
│   ├── api/           # FastAPI routes
│   ├── ai/            # Gemini prompts & extraction
│   ├── image/         # OpenCV preprocessing
│   ├── models/        # Data storage
│   ├── schemas/       # Pydantic models
│   ├── services/      # Business logic
│   ├── utils/         # Helpers, logging, exceptions
│   ├── config.py      # Settings
│   └── main.py        # App entry point
├── uploads/           # Uploaded images
├── outputs/           # Processed outputs
├── tests/             # Test suite
└── requirements.txt   # Dependencies
```

## License

MIT
