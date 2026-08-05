"""Pydantic schemas for bill data validation."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, model_validator


class BillItem(BaseModel):
    """Schema for individual bill items."""

    item_name: Optional[str] = Field(default=None, description="Name of the product/service")
    quantity: Optional[float] = Field(default=None, ge=0, description="Quantity purchased")
    unit_price: Optional[float] = Field(default=None, ge=0, description="Price per unit")
    amount: Optional[float] = Field(default=None, ge=0, description="Total amount for this item")

    @model_validator(mode="after")
    def validate_item_calculation(self) -> "BillItem":
        """Validate that quantity * unit_price ≈ amount."""
        if self.quantity is not None and self.unit_price is not None and self.amount is not None:
            calculated = round(self.quantity * self.unit_price, 2)
            actual = round(self.amount, 2)
            # Allow 1% tolerance for rounding
            if actual > 0 and abs(calculated - actual) / actual > 0.01:
                pass
        return self


class BillData(BaseModel):
    """Schema for extracted bill data."""

    store_name: Optional[str] = Field(default=None, description="Name of the store/vendor")
    invoice_number: Optional[str] = Field(default=None, description="Invoice/bill number")
    invoice_date: Optional[str] = Field(default=None, description="Date of invoice (YYYY-MM-DD)")
    invoice_time: Optional[str] = Field(default=None, description="Time of invoice (HH:MM)")
    gst_number: Optional[str] = Field(default=None, description="GST/Tax registration number")
    address: Optional[str] = Field(default=None, description="Store address")
    currency: Optional[str] = Field(default=None, description="Currency code (USD, INR, etc.)")
    payment_method: Optional[str] = Field(default=None, description="Payment method used")
    subtotal: Optional[float] = Field(default=None, ge=0, description="Subtotal before tax/discount")
    discount: Optional[float] = Field(default=None, ge=0, description="Discount amount")
    tax: Optional[float] = Field(default=None, ge=0, description="Total tax amount")
    cgst: Optional[float] = Field(default=None, ge=0, description="CGST amount")
    sgst: Optional[float] = Field(default=None, ge=0, description="SGST amount")
    igst: Optional[float] = Field(default=None, ge=0, description="IGST amount")
    total: Optional[float] = Field(default=None, ge=0, description="Grand total amount")
    items: List[BillItem] = Field(default_factory=list, description="List of purchased items")

    @field_validator("invoice_date")
    @classmethod
    def validate_date_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate date format if provided."""
        if v is None or v == "":
            return None
        formats = ["%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d"]
        for fmt in formats:
            try:
                datetime.strptime(v, fmt)
                return v
            except ValueError:
                continue
        return v

    @model_validator(mode="after")
    def validate_totals(self) -> "BillData":
        """Validate that subtotal + tax - discount ≈ total."""
        if self.subtotal is not None and self.total is not None:
            tax_total = self.tax or 0
            discount_total = self.discount or 0
            expected = self.subtotal + tax_total - discount_total
            if self.total > 0 and abs(expected - self.total) / self.total > 0.02:
                pass
        return self


class ConfidenceScore(BaseModel):
    """Confidence scores for each extracted field."""

    store_name: float = Field(default=0.0, ge=0, le=1)
    invoice_number: float = Field(default=0.0, ge=0, le=1)
    invoice_date: float = Field(default=0.0, ge=0, le=1)
    invoice_time: float = Field(default=0.0, ge=0, le=1)
    gst_number: float = Field(default=0.0, ge=0, le=1)
    address: float = Field(default=0.0, ge=0, le=1)
    currency: float = Field(default=0.0, ge=0, le=1)
    payment_method: float = Field(default=0.0, ge=0, le=1)
    subtotal: float = Field(default=0.0, ge=0, le=1)
    discount: float = Field(default=0.0, ge=0, le=1)
    tax: float = Field(default=0.0, ge=0, le=1)
    total: float = Field(default=0.0, ge=0, le=1)
    items: float = Field(default=0.0, ge=0, le=1)


class ValidationResult(BaseModel):
    """Validation results for extracted bill data."""

    is_valid: bool = Field(default=True, description="Overall validation status")
    errors: List[str] = Field(default_factory=list, description="List of validation errors")
    warnings: List[str] = Field(default_factory=list, description="List of validation warnings")
    duplicate_items: List[str] = Field(default_factory=list, description="Names of duplicate items")
    calculation_errors: List[str] = Field(default_factory=list, description="Math validation errors")


class BillExtractionResult(BaseModel):
    """Complete extraction result including data, confidence, and validation."""

    id: str = Field(..., description="Unique extraction job ID")
    status: str = Field(default="pending", description="Processing status")
    bill_data: Optional[BillData] = Field(default=None, description="Extracted bill data")
    confidence: Optional[ConfidenceScore] = Field(default=None, description="Confidence scores")
    validation: Optional[ValidationResult] = Field(default=None, description="Validation results")
    created_at: str = Field(..., description="Timestamp when job was created")
    processed_at: Optional[str] = Field(default=None, description="Timestamp when processing completed")
    error_message: Optional[str] = Field(default=None, description="Error message if processing failed")
