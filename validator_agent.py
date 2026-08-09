import json
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ======================================================
# SYSTEM PROMPT (HARDENED – NO INVENTION ALLOWED)
# ======================================================

VALIDATOR_SYSTEM_PROMPT = """
You are an expert financial document auditor.

Your role is VALIDATION, not extraction.

ABSOLUTE RULES (MANDATORY):
- You MUST NOT add new line items.
- You MUST NOT remove line items.
- You MUST NOT invent missing values.
- You MUST NOT create invoice numbers, dates, totals, vendors, or customers.
- You MUST NOT introduce fields that are not already present.
- You MAY ONLY modify existing numeric values if the correction is mathematically provable.

Allowed corrections:
- Fix numeric formatting (e.g., "1,234.00" → 1234.00)
- Fix obvious OCR decimal placement errors
- Normalize dates to ISO format YYYY-MM-DD
- Recalculate line_total ONLY if quantity and unit_price are present AND
  the correction matches the printed value format

Totals rules (STRICT):
- Printed subtotal, tax, and total are the authoritative source of truth
- You MUST NOT change subtotal, tax, or total if they are present
- If calculated values differ from printed values, DO NOT modify them
- Instead, add an issue describing the discrepancy
- Recalculation of subtotal or total is allowed ONLY if the printed value is null
- NEVER apply rounding unless explicitly stated in the document
- If printed and calculated values are equal (exactly or within 0.01),
  DO NOT log a discrepancy

Tax handling (CRITICAL):
- Tax must NEVER be recalculated unless an explicit tax rate is printed
- If tax rate is absent, treat tax as informational only
- Tax discrepancies alone must NOT invalidate the invoice

Disallowed actions:
- Adding new line_items
- Guessing missing quantities or prices
- Guessing invoice_number or dates
- Merging or splitting line items

VALIDATION PHILOSOPHY (MANDATORY):
- This is a deterministic validation task, not an inference task
- Printed invoice values are authoritative
- Calculations are advisory only
- Corrections must be provable, not inferred
- Silence is forbidden: every correction or discrepancy must be logged

Validity rule:
- Set is_valid = false ONLY if required fields are missing
  or a material, provable inconsistency exists
- Warnings alone must NOT invalidate the invoice

OUTPUT FORMAT (STRICT):
{
  "validated_invoice": { ... corrected invoice JSON ... },
  "issues": [ "string", "string" ],
  "is_valid": boolean
}

"""

# ======================================================
# PROMPT BUILDER
# ======================================================

def build_validator_prompt(invoice_json: dict) -> str:
    return f"""
EXTRACTED INVOICE JSON (DO NOT ADD OR REMOVE DATA):

{json.dumps(invoice_json, indent=2)}

Validate ONLY what exists above.
Return corrected JSON strictly following the required output schema.
"""

# ======================================================
# POST-VALIDATION GUARDRAILS (NO INVENTION)
# ======================================================

def enforce_no_invention(original: dict, validated: dict) -> dict:
    """
    Hard safety check to ensure validator did NOT invent data.
    Raises ValueError if illegal modification detected.
    """

    validated_invoice = validated.get("validated_invoice", {})

    # ---- Line items count must match ----
    orig_items = original.get("line_items", [])
    new_items = validated_invoice.get("line_items", [])

    if len(orig_items) != len(new_items):
        raise ValueError("Validator attempted to add/remove line items")

    # ---- Invoice number cannot be invented ----
    if original.get("invoice_number") is None and validated_invoice.get("invoice_number") is not None:
        raise ValueError("Validator attempted to invent invoice_number")

    # ---- Totals cannot be invented ----
    orig_totals = original.get("totals", {})
    new_totals = validated_invoice.get("totals", {})

    for key in ["subtotal", "tax", "total"]:
        if orig_totals.get(key) is None and new_totals.get(key) is not None:
            raise ValueError(f"Validator attempted to invent total field: {key}")

    return validated

# ======================================================
# MAIN VALIDATOR FUNCTION
# ======================================================

def validate_invoice(extracted_json: dict) -> dict:
    prompt = build_validator_prompt(extracted_json)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": VALIDATOR_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
    )

    content = response.choices[0].message.content

    try:
        result = json.loads(content)
        result = enforce_no_invention(extracted_json, result)
        return result

    except ValueError as e:
        return {
            "validated_invoice": extracted_json,
            "issues": [str(e)],
            "is_valid": False
        }

    except json.JSONDecodeError:
        return {
            "validated_invoice": extracted_json,
            "issues": ["Validator returned invalid JSON"],
            "is_valid": False
        }

# ======================================================
# TEST MODULE
# ======================================================

if __name__ == "__main__":
    from Azure_invoice_ocr import azure_extract_invoice
    from extractor import extract_invoice_from_ocr

    file_path = r"sample_invoice_1.pdf"

    ocr = azure_extract_invoice(file_path)
    extracted = extract_invoice_from_ocr(ocr)
    validated = validate_invoice(extracted)

    print(json.dumps(validated, indent=2))

