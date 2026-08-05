"""Image preprocessing using OpenCV and Pillow."""

import io
import tempfile
from pathlib import Path
from typing import Tuple, Optional
import logging

import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

from app.utils.logger import get_logger
from app.utils.exceptions import ImageProcessingError

logger = get_logger(__name__)


class ImageProcessor:
    """Handles all image preprocessing operations."""

    def __init__(self, max_dimension: int = 2048, quality: int = 95):
        self.max_dimension = max_dimension
        self.quality = quality
        self._supported_formats = {"JPEG", "JPG", "PNG", "PDF"}

    async def process(self, image_bytes: bytes, mime_type: str) -> bytes:
        """
        Main preprocessing pipeline.

        Steps:
        1. Load image
        2. Auto-rotate
        3. Resize if too large
        4. Convert to grayscale
        5. Denoise
        6. Sharpen
        7. Enhance contrast
        8. Adaptive thresholding
        9. Crop borders
        10. Encode to optimized bytes
        """
        try:
            if mime_type == "application/pdf":
                image_bytes = await self._pdf_to_image(image_bytes)

            np_arr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            if img is None:
                raise ImageProcessingError("Failed to decode image")

            logger.info("Starting image preprocessing", 
                       original_shape=img.shape, 
                       mime_type=mime_type)

            img = self._auto_rotate(img)
            img = self._resize_if_needed(img)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
            kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
            sharpened = cv2.filter2D(denoised, -1, kernel)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            contrasted = clahe.apply(sharpened)
            binary = cv2.adaptiveThreshold(
                contrasted, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                11, 2
            )
            cropped = self._crop_borders(binary)

            success, encoded = cv2.imencode(".png", cropped)
            if not success:
                raise ImageProcessingError("Failed to encode processed image")

            processed_bytes = encoded.tobytes()

            logger.info("Image preprocessing completed",
                       processed_size=len(processed_bytes),
                       final_shape=cropped.shape)

            return processed_bytes

        except ImageProcessingError:
            raise
        except Exception as e:
            logger.error("Image preprocessing failed", error=str(e))
            raise ImageProcessingError(f"Preprocessing failed: {str(e)}")

    def _auto_rotate(self, img: np.ndarray) -> np.ndarray:
        """Detect and correct image rotation based on text orientation."""
        try:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            angles = [0, 90, 180, 270]
            best_angle = 0
            max_score = 0

            for angle in angles:
                rotated = self._rotate_image(gray, angle)
                edges = cv2.Canny(rotated, 50, 150)
                lines = cv2.HoughLinesP(edges, 1, np.pi/180, 100, minLineLength=100, maxLineGap=10)

                if lines is not None:
                    horizontal_score = sum(
                        1 for line in lines 
                        if abs(line[0][3] - line[0][1]) < abs(line[0][2] - line[0][0])
                    )
                    if horizontal_score > max_score:
                        max_score = horizontal_score
                        best_angle = angle

            if best_angle != 0:
                return self._rotate_image(img, best_angle)
            return img

        except Exception as e:
            logger.warning("Auto-rotation failed, using original", error=str(e))
            return img

    def _rotate_image(self, img: np.ndarray, angle: int) -> np.ndarray:
        """Rotate image by given angle."""
        if angle == 0:
            return img

        (h, w) = img.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)

        cos = abs(M[0, 0])
        sin = abs(M[0, 1])
        new_w = int((h * sin) + (w * cos))
        new_h = int((h * cos) + (w * sin))

        M[0, 2] += (new_w / 2) - center[0]
        M[1, 2] += (new_h / 2) - center[1]

        return cv2.warpAffine(img, M, (new_w, new_h), borderValue=(255, 255, 255))

    def _resize_if_needed(self, img: np.ndarray) -> np.ndarray:
        """Resize image if dimensions exceed maximum."""
        height, width = img.shape[:2]
        max_dim = max(height, width)

        if max_dim > self.max_dimension:
            scale = self.max_dimension / max_dim
            new_width = int(width * scale)
            new_height = int(height * scale)
            resized = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)
            logger.info("Image resized", 
                       original=(width, height), 
                       new=(new_width, new_height))
            return resized
        return img

    def _crop_borders(self, img: np.ndarray) -> np.ndarray:
        """Crop unnecessary white/black borders."""
        try:
            if len(img.shape) == 3:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            else:
                gray = img

            _, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            if not contours:
                return img

            x_min = min(cv2.boundingRect(c)[0] for c in contours)
            y_min = min(cv2.boundingRect(c)[1] for c in contours)
            x_max = max(cv2.boundingRect(c)[0] + cv2.boundingRect(c)[2] for c in contours)
            y_max = max(cv2.boundingRect(c)[1] + cv2.boundingRect(c)[3] for c in contours)

            padding = 10
            h, w = img.shape[:2]
            x_min = max(0, x_min - padding)
            y_min = max(0, y_min - padding)
            x_max = min(w, x_max + padding)
            y_max = min(h, y_max + padding)

            return img[y_min:y_max, x_min:x_max]

        except Exception as e:
            logger.warning("Border cropping failed", error=str(e))
            return img

    async def _pdf_to_image(self, pdf_bytes: bytes) -> bytes:
        """Convert first page of PDF to image."""
        try:
            from pdf2image import convert_from_bytes
            images = convert_from_bytes(pdf_bytes, first_page=1, last_page=1, dpi=200)
            if not images:
                raise ImageProcessingError("PDF contains no pages")

            img_byte_arr = io.BytesIO()
            images[0].save(img_byte_arr, format="PNG")
            return img_byte_arr.getvalue()

        except ImportError:
            logger.error("pdf2image not installed, cannot process PDF")
            raise ImageProcessingError("PDF processing requires pdf2image. Install with: pip install pdf2image")
        except Exception as e:
            raise ImageProcessingError(f"PDF conversion failed: {str(e)}")

    def get_image_dimensions(self, image_bytes: bytes) -> Tuple[int, int]:
        """Get image dimensions without full decode."""
        try:
            img = Image.open(io.BytesIO(image_bytes))
            return img.size
        except Exception:
            return (0, 0)


# Global processor instance
image_processor = ImageProcessor()
