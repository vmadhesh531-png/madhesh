"""Main processing orchestrator."""

from typing import Optional
from pathlib import Path

from app.config import settings
from app.models.storage import job_storage
from app.image.processor import image_processor
from app.ai.extractor import gemini_extractor
from app.services.validator import bill_validator
from app.schemas.bill import BillExtractionResult, BillData, ConfidenceScore, ValidationResult
from app.utils.logger import get_logger
from app.utils.helpers import format_datetime
from app.utils.exceptions import AIBillException

logger = get_logger(__name__)


class BillProcessor:
    """Orchestrates the complete bill extraction workflow."""

    async def process_image(
        self, 
        job_id: str, 
        image_bytes: bytes, 
        mime_type: str,
        preprocess: bool = True
    ) -> BillExtractionResult:
        """
        Process image through complete pipeline.

        Workflow:
        1. Preprocess image (if enabled)
        2. Extract data using Gemini
        3. Validate extracted data
        4. Store and return result
        """
        try:
            result = await job_storage.get(job_id)
            if result:
                result.status = "processing"
                await job_storage.update(job_id, result)

            if preprocess:
                logger.info("Preprocessing image", job_id=job_id)
                processed_image = await image_processor.process(image_bytes, mime_type)
            else:
                processed_image = image_bytes

            logger.info("Starting AI extraction", job_id=job_id)
            raw_extraction = await gemini_extractor.extract(processed_image, "image/png")

            bill_data, confidence = gemini_extractor._map_to_bill_data(raw_extraction)

            logger.info("Running validation", job_id=job_id)
            validation = bill_validator.validate(bill_data)

            final_result = BillExtractionResult(
                id=job_id,
                status="completed",
                bill_data=bill_data,
                confidence=confidence,
                validation=validation,
                created_at=result.created_at if result else format_datetime(),
                processed_at=format_datetime()
            )

            await job_storage.update(job_id, final_result)

            logger.info("Processing completed successfully", 
                       job_id=job_id,
                       store_name=bill_data.store_name,
                       total=bill_data.total)

            return final_result

        except AIBillException:
            result = await job_storage.get(job_id)
            if result:
                result.status = "failed"
                result.error_message = str(AIBillException)
                await job_storage.update(job_id, result)
            raise
        except Exception as e:
            logger.error("Processing failed unexpectedly", job_id=job_id, error=str(e))
            result = await job_storage.get(job_id)
            if result:
                result.status = "failed"
                result.error_message = f"Internal error: {str(e)}"
                await job_storage.update(job_id, result)
            raise


# Global processor instance
bill_processor = BillProcessor()
