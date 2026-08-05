"""FastAPI routes for the AI Image-to-Bill module."""

import io
import magic
from typing import Optional

from fastapi import APIRouter, File, UploadFile, HTTPException, Form, Depends
from fastapi.responses import JSONResponse

from app.config import settings
from app.models.storage import job_storage
from app.services.processor import bill_processor
from app.schemas.bill import BillExtractionResult
from app.schemas.requests import ImageUploadResponse, ExtractBillRequest, ValidateRequest
from app.utils.logger import get_logger
from app.utils.helpers import generate_id, generate_file_hash, sanitize_filename
from app.utils.exceptions import AIBillException, NotFoundError

logger = get_logger(__name__)

router = APIRouter(prefix="/api")


@router.post("/upload-image", response_model=ImageUploadResponse)
async def upload_image(
    file: UploadFile = File(..., description="Image file (JPG, PNG, PDF)"),
    preprocess: bool = Form(default=True, description="Enable image preprocessing")
):
    """
    Upload an image for bill extraction.

    - **file**: Image file (JPG, JPEG, PNG, PDF)
    - **preprocess**: Whether to apply image preprocessing (default: true)
    - Max file size: 20MB
    """
    try:
        contents = await file.read()
        if len(contents) > settings.max_upload_size:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {settings.max_upload_size / (1024*1024):.0f}MB"
            )

        mime = magic.from_buffer(contents, mime=True)
        if mime not in settings.allowed_mime_types:
            raise HTTPException(
                status_code=415,
                detail=f"Unsupported file type: {mime}. Allowed: {', '.join(settings.allowed_mime_types)}"
            )

        job_id = generate_id()
        file_hash = generate_file_hash(contents)
        safe_filename = sanitize_filename(file.filename or "unknown")

        file_path = settings.upload_path / f"{job_id}_{safe_filename}"
        with open(file_path, "wb") as f:
            f.write(contents)

        await job_storage.create(job_id)

        logger.info("Image uploaded successfully",
                   job_id=job_id,
                   filename=safe_filename,
                   size=len(contents),
                   mime_type=mime)

        return ImageUploadResponse(
            id=job_id,
            filename=safe_filename,
            file_hash=file_hash,
            status="uploaded",
            message="Image uploaded successfully. Use /api/extract-bill to process."
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Upload failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.post("/extract-bill", response_model=BillExtractionResult)
async def extract_bill(request: ExtractBillRequest):
    """
    Extract bill data from previously uploaded image.

    - **id**: Job ID returned from /upload-image
    - **preprocess**: Whether to preprocess image (default: true)
    - **language_hint**: Optional language hint for better OCR
    """
    try:
        job = await job_storage.get(request.id)
        if not job:
            raise NotFoundError(f"Job {request.id} not found")

        upload_dir = settings.upload_path
        file_pattern = f"{request.id}_*"
        matching_files = list(upload_dir.glob(file_pattern))

        if not matching_files:
            raise NotFoundError(f"Uploaded file for job {request.id} not found")

        file_path = matching_files[0]

        with open(file_path, "rb") as f:
            image_bytes = f.read()

        mime = magic.from_buffer(image_bytes, mime=True)

        result = await bill_processor.process_image(
            job_id=request.id,
            image_bytes=image_bytes,
            mime_type=mime,
            preprocess=request.preprocess
        )

        return result

    except AIBillException as e:
        logger.error("Extraction failed", job_id=request.id, error=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Extraction failed unexpectedly", job_id=request.id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")


@router.post("/validate", response_model=BillExtractionResult)
async def validate_bill(request: ValidateRequest):
    """
    Re-run validation on extracted bill data.

    - **id**: Job ID to validate
    """
    try:
        job = await job_storage.get(request.id)
        if not job:
            raise NotFoundError(f"Job {request.id} not found")

        if not job.bill_data:
            raise HTTPException(
                status_code=400,
                detail="No bill data found. Run /extract-bill first."
            )

        from app.services.validator import bill_validator
        validation = bill_validator.validate(job.bill_data)
        job.validation = validation

        await job_storage.update(request.id, job)

        return job

    except AIBillException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Validation failed", job_id=request.id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


@router.get("/result/{id}", response_model=BillExtractionResult)
async def get_result(id: str):
    """
    Get extraction result by job ID.

    - **id**: Job ID from upload or extraction
    """
    try:
        result = await job_storage.get(id)
        if not result:
            raise NotFoundError(f"Result {id} not found")

        return result

    except AIBillException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "ai-image-to-bill",
        "version": settings.app_version
    }
