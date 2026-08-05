"""Google Gemini AI extraction logic."""

import json
import base64
from typing import Optional, Dict, Any
import asyncio

import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.schemas.bill import BillData, ConfidenceScore, BillExtractionResult
from app.ai.prompts import BILL_EXTRACTION_PROMPT
from app.utils.logger import get_logger
from app.utils.exceptions import AIExtractionError
from app.utils.helpers import format_datetime

logger = get_logger(__name__)


class GeminiExtractor:
    """Handles AI extraction using Google Gemini."""

    def __init__(self):
        self.api_key = settings.gemini_api_key
        self.model_name = settings.gemini_model
        self._configure_gemini()
        self.model = genai.GenerativeModel(self.model_name)

    def _configure_gemini(self) -> None:
        """Configure Gemini API with API key."""
        genai.configure(api_key=self.api_key)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True
    )
    async def extract(self, image_bytes: bytes, mime_type: str = "image/png") -> Dict[str, Any]:
        """
        Extract bill data from image using Gemini Vision.

        Args:
            image_bytes: Processed image bytes
            mime_type: MIME type of the image

        Returns:
            Dict containing extracted data and confidence scores
        """
        try:
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")

            image_part = {
                "mime_type": mime_type,
                "data": image_b64
            }

            logger.info("Sending image to Gemini for extraction",
                       model=self.model_name,
                       image_size=len(image_bytes))

            response = await asyncio.to_thread(
                self.model.generate_content,
                [BILL_EXTRACTION_PROMPT, image_part],
                generation_config=genai.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=4096,
                    response_mime_type="application/json"
                )
            )

            raw_text = response.text
            raw_text = raw_text.strip()
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            if raw_text.startswith("```"):
                raw_text = raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
            raw_text = raw_text.strip()

            extracted_data = json.loads(raw_text)

            logger.info("Extraction completed successfully",
                       fields_extracted=len([v for v in extracted_data.values() if v is not None]))

            return extracted_data

        except json.JSONDecodeError as e:
            logger.error("Failed to parse Gemini response as JSON", 
                        error=str(e),
                        raw_response=raw_text[:500])
            raise AIExtractionError(f"Invalid JSON response from AI: {str(e)}")
        except Exception as e:
            logger.error("Gemini extraction failed", error=str(e))
            raise AIExtractionError(f"AI extraction failed: {str(e)}")

    def _map_to_bill_data(self, extracted: Dict[str, Any]) -> tuple[BillData, ConfidenceScore]:
        """Map raw extraction to BillData and ConfidenceScore schemas."""

        confidence_raw = extracted.pop("confidence", {})

        items_raw = extracted.get("items", []) or []
        items = []
        for item in items_raw:
            if isinstance(item, dict):
                items.append({
                    "item_name": item.get("item_name"),
                    "quantity": self._safe_float(item.get("quantity")),
                    "unit_price": self._safe_float(item.get("unit_price")),
                    "amount": self._safe_float(item.get("amount"))
                })

        bill_data = BillData(
            store_name=extracted.get("store_name"),
            invoice_number=extracted.get("invoice_number"),
            invoice_date=extracted.get("invoice_date"),
            invoice_time=extracted.get("invoice_time"),
            gst_number=extracted.get("gst_number"),
            address=extracted.get("address"),
            currency=extracted.get("currency"),
            payment_method=extracted.get("payment_method"),
            subtotal=self._safe_float(extracted.get("subtotal")),
            discount=self._safe_float(extracted.get("discount")),
            tax=self._safe_float(extracted.get("tax")),
            cgst=self._safe_float(extracted.get("cgst")),
            sgst=self._safe_float(extracted.get("sgst")),
            igst=self._safe_float(extracted.get("igst")),
            total=self._safe_float(extracted.get("total")),
            items=items
        )

        confidence = ConfidenceScore(
            store_name=confidence_raw.get("store_name", 0.0),
            invoice_number=confidence_raw.get("invoice_number", 0.0),
            invoice_date=confidence_raw.get("invoice_date", 0.0),
            invoice_time=confidence_raw.get("invoice_time", 0.0),
            gst_number=confidence_raw.get("gst_number", 0.0),
            address=confidence_raw.get("address", 0.0),
            currency=confidence_raw.get("currency", 0.0),
            payment_method=confidence_raw.get("payment_method", 0.0),
            subtotal=confidence_raw.get("subtotal", 0.0),
            discount=confidence_raw.get("discount", 0.0),
            tax=confidence_raw.get("tax", 0.0),
            total=confidence_raw.get("total", 0.0),
            items=confidence_raw.get("items", 0.0)
        )

        return bill_data, confidence

    def _safe_float(self, value: Any) -> Optional[float]:
        """Safely convert value to float."""
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            cleaned = value.strip().replace(",", "").replace("$", "").replace("₹", "").replace("€", "").replace("£", "")
            try:
                return float(cleaned)
            except ValueError:
                return None
        return None


# Global extractor instance
gemini_extractor = GeminiExtractor()
