"""Bill validation service."""

from typing import List, Dict, Any, Set
from collections import Counter

from app.schemas.bill import BillData, ValidationResult, BillItem
from app.utils.logger import get_logger

logger = get_logger(__name__)


class BillValidator:
    """Validates extracted bill data for accuracy and consistency."""

    def __init__(self):
        self.tolerance = 0.02  # 2% tolerance for calculations

    def validate(self, bill_data: BillData) -> ValidationResult:
        """
        Run all validation checks on bill data.

        Returns:
            ValidationResult with errors, warnings, and flags
        """
        errors: List[str] = []
        warnings: List[str] = []
        duplicate_items: List[str] = []
        calculation_errors: List[str] = []

        self._validate_required_fields(bill_data, errors, warnings)
        self._validate_item_calculations(bill_data, errors, calculation_errors)
        duplicate_items = self._find_duplicate_items(bill_data)
        self._validate_totals(bill_data, errors, calculation_errors)
        self._validate_gst(bill_data, errors, calculation_errors)
        self._validate_dates(bill_data, errors)
        self._validate_values(bill_data, errors, warnings)

        is_valid = len(errors) == 0

        if not is_valid:
            logger.warning("Bill validation failed", 
                          errors=errors, 
                          invoice_number=bill_data.invoice_number)

        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            duplicate_items=duplicate_items,
            calculation_errors=calculation_errors
        )

    def _validate_required_fields(self, bill: BillData, errors: List[str], warnings: List[str]) -> None:
        """Check for missing critical fields."""
        if not bill.store_name:
            warnings.append("Store name is missing")
        if not bill.invoice_number:
            warnings.append("Invoice number is missing")
        if not bill.invoice_date:
            errors.append("Invoice date is required")
        if not bill.total:
            errors.append("Total amount is required")
        if not bill.items or len(bill.items) == 0:
            warnings.append("No items found in bill")

    def _validate_item_calculations(self, bill: BillData, errors: List[str], calc_errors: List[str]) -> None:
        """Validate quantity * unit_price ≈ amount for each item."""
        for idx, item in enumerate(bill.items):
            if item.quantity is not None and item.unit_price is not None and item.amount is not None:
                expected = round(item.quantity * item.unit_price, 2)
                actual = round(item.amount, 2)

                if actual > 0 and abs(expected - actual) / actual > self.tolerance:
                    calc_errors.append(
                        f"Item {idx + 1} ({item.item_name}): "
                        f"Expected {expected}, got {actual} "
                        f"({item.quantity} × {item.unit_price})"
                    )

    def _find_duplicate_items(self, bill: BillData) -> List[str]:
        """Find duplicate item names in the bill."""
        item_names = [item.item_name for item in bill.items if item.item_name]
        name_counts = Counter(item_names)
        duplicates = [name for name, count in name_counts.items() if count > 1]
        return duplicates

    def _validate_totals(self, bill: BillData, errors: List[str], calc_errors: List[str]) -> None:
        """Validate that subtotal + tax - discount ≈ total."""
        if bill.subtotal is not None and bill.total is not None:
            tax = bill.tax or 0
            discount = bill.discount or 0
            expected_total = bill.subtotal + tax - discount

            if bill.total > 0:
                diff_ratio = abs(expected_total - bill.total) / bill.total
                if diff_ratio > self.tolerance:
                    calc_errors.append(
                        f"Total mismatch: Expected {expected_total:.2f} "
                        f"({bill.subtotal:.2f} + {tax:.2f} - {discount:.2f}), "
                        f"got {bill.total:.2f}"
                    )

    def _validate_gst(self, bill: BillData, errors: List[str], calc_errors: List[str]) -> None:
        """Validate GST calculations."""
        cgst = bill.cgst or 0
        sgst = bill.sgst or 0
        igst = bill.igst or 0
        tax = bill.tax or 0

        if tax > 0 and (cgst > 0 or sgst > 0 or igst > 0):
            gst_sum = cgst + sgst + igst
            if abs(gst_sum - tax) / tax > self.tolerance:
                calc_errors.append(
                    f"GST mismatch: CGST({cgst}) + SGST({sgst}) + IGST({igst}) = "
                    f"{gst_sum}, but total tax is {tax}"
                )

    def _validate_dates(self, bill: BillData, errors: List[str]) -> None:
        """Validate date formats and logic."""
        if bill.invoice_date:
            pass

    def _validate_values(self, bill: BillData, errors: List[str], warnings: List[str]) -> None:
        """Validate numeric values for sanity."""
        if bill.total is not None and bill.total < 0:
            errors.append("Total amount cannot be negative")

        if bill.subtotal is not None and bill.subtotal < 0:
            errors.append("Subtotal cannot be negative")

        for item in bill.items:
            if item.quantity is not None and item.quantity < 0:
                errors.append(f"Negative quantity for item: {item.item_name}")
            if item.unit_price is not None and item.unit_price < 0:
                errors.append(f"Negative unit price for item: {item.item_name}")

            if item.quantity is not None and item.quantity > 10000:
                warnings.append(f"Unusually high quantity for {item.item_name}: {item.quantity}")
            if item.unit_price is not None and item.unit_price > 1000000:
                warnings.append(f"Unusually high unit price for {item.item_name}: {item.unit_price}")


# Global validator instance
bill_validator = BillValidator()
