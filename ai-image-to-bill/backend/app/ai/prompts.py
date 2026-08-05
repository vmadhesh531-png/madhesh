"""Gemini prompts separated from application logic."""

BILL_EXTRACTION_PROMPT = """You are an expert OCR and data extraction system specialized in reading invoices, bills, and receipts from images.

Your task is to extract ALL visible information from the provided image and return it as a strict JSON object.

EXTRACTION RULES:
1. Extract text exactly as it appears - do not correct spelling unless obviously garbled
2. For monetary values, extract only the numeric value (remove currency symbols in your output but note the currency)
3. If a field is not present in the image, set it to null
4. Do NOT hallucinate or invent values
5. For dates, prefer ISO format (YYYY-MM-DD) if possible, otherwise preserve original format
6. For items table, extract each row as a separate item object
7. Calculate confidence score (0.0-1.0) for each field based on clarity/visibility

FIELDS TO EXTRACT:
- store_name: Store or business name
- invoice_number: Bill/invoice number
- invoice_date: Date on the bill
- invoice_time: Time on the bill (if present)
- gst_number: GST/VAT/Tax registration number
- address: Store address
- currency: Currency code (USD, INR, EUR, etc.) - infer from symbols or text
- payment_method: How payment was made (Cash, Card, UPI, etc.)
- subtotal: Amount before tax/discount
- discount: Discount amount (if any)
- tax: Total tax amount
- cgst: CGST amount (India)
- sgst: SGST amount (India)
- igst: IGST amount (India)
- total: Grand total/final amount
- items: Array of items with:
  - item_name: Product/service name
  - quantity: Number of units
  - unit_price: Price per unit
  - amount: Line total (quantity * unit_price)

VALIDATION RULES:
- Ensure quantity * unit_price ≈ amount for each item
- Ensure subtotal + tax - discount ≈ total
- Flag any calculation discrepancies

RESPONSE FORMAT - Return ONLY this JSON structure, no markdown, no explanations:

{
  "store_name": null,
  "invoice_number": null,
  "invoice_date": null,
  "invoice_time": null,
  "gst_number": null,
  "address": null,
  "currency": null,
  "payment_method": null,
  "subtotal": null,
  "discount": null,
  "tax": null,
  "cgst": null,
  "sgst": null,
  "igst": null,
  "total": null,
  "items": [
    {
      "item_name": null,
      "quantity": null,
      "unit_price": null,
      "amount": null
    }
  ],
  "confidence": {
    "store_name": 0.0,
    "invoice_number": 0.0,
    "invoice_date": 0.0,
    "invoice_time": 0.0,
    "gst_number": 0.0,
    "address": 0.0,
    "currency": 0.0,
    "payment_method": 0.0,
    "subtotal": 0.0,
    "discount": 0.0,
    "tax": 0.0,
    "total": 0.0,
    "items": 0.0
  }
}

IMPORTANT:
- Return ONLY valid JSON
- Never return markdown code blocks
- Unknown values MUST be null
- Confidence scores must be between 0.0 and 1.0
- Do not include any text outside the JSON
"""

VALIDATION_PROMPT = """You are a bill validation expert. Review the extracted bill data and identify any issues.

Check for:
1. Calculation errors (subtotal + tax - discount should equal total)
2. Missing required fields
3. Duplicate items in the items list
4. Invalid date formats
5. Negative values where they shouldn't exist
6. GST calculation errors (CGST + SGST + IGST should equal total tax)
7. Suspicious values (extremely high amounts, unrealistic quantities)

Return ONLY a JSON object with this structure:

{
  "is_valid": true,
  "errors": [],
  "warnings": [],
  "duplicate_items": [],
  "calculation_errors": []
}

No markdown, no explanations outside JSON.
"""
