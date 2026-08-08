import os
import json
from typing import Any, Dict
from dotenv import load_dotenv
from openai import OpenAI
from Azure_invoice_ocr import azure_extract_invoice
load_dotenv()
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# -------------------------------
# System prompt for extractor agent
# -------------------------------

EXTRACTOR_SYSTEM_PROMPT = """
You are an expert invoice extraction engine.

Your job:
- Read noisy OCR text from an invoice.
- Infer all key fields.
- Output a STRICT JSON object matching the requested schema.
- If something is missing, use null instead of guessing wildly.
- Use numbers (not strings) for numeric values.
- Use ISO date format YYYY-MM-DD where possible.

Schema (JSON object):
{
  "invoice_number": string or null,
  "invoice_date": string or null,      // ISO 8601: YYYY-MM-DD
  "due_date": string or null,          // payment due date, ISO
  "currency": string or null,          // e.g. "USD", "EUR"

  "vendor": {
    "name": string or null,
    "address": string or null
  },

  "customer": {
    "name": string or null,
    "address": string or null
  },

  "totals": {
    "subtotal": number or null,
    "tax": number or null,
    "total": number or null,
    "prepaid": number or null,
    "remainder": number or null
  },

  "payment_terms": string or null,

  "line_items": [
    {
      "line_number": integer or null,
      "item_code": string or null,
      "description": string or null,
      "quantity": number or null,
      "unit": string or null,
      "unit_price": number or null,
      "discount_percent": number or null,
      "line_total": number or null
    }
  ]
}

Rules:
- Always return valid JSON. No comments, no trailing commas, no extra text.
- If you see currency symbols or mentions like "USD", set the currency field.
- If invoice date is written as M/D/YYYY or D/M/YYYY, convert to YYYY-MM-DD.
- If there are more than 100 line items, you may include only the first 100.
- Ignore footer text, boilerplate notes, and non-financial content.
"""

# -------------------------------
# Helper: build user prompt from OCR output
# -------------------------------
def build_extractor_prompt(ocr_result: Dict[str, Any]) -> str:
    """
    Turn OCR output into a single prompt string for GPT.
    Expects ocr_result from your extract_text() function:
      { "full_text": "...", "pages": [...], "tables": [...] }
    """
    full_text = ocr_result.get("full_text", "") or ""

    # Optionally, we can also serialize tables to help GPT with structure
    tables = ocr_result.get("tables", [])
    tables_text = ""
    if tables:
        tables_text_lines = []
        for t_idx, table in enumerate(tables):
            tables_text_lines.append(f"TABLE {t_idx+1}:")
            for row in table:
                # Join row cells with a separator so GPT sees them as columns
                row_str = " | ".join(str(c) for c in row if c is not None)
                tables_text_lines.append(row_str)
            tables_text_lines.append("")  # blank line between tables
        tables_text = "\n".join(tables_text_lines)

    prompt = f"""
You are given OCR text (and optional table text) from an invoice.

OCR FULL TEXT:
----------------
{full_text}
----------------

OCR TABLES (if any):
----------------
{tables_text}
----------------

Using ONLY this information, extract the invoice into the JSON schema described.
Remember:
- JSON object only
- No extra commentary
- Use null for anything missing or truly ambiguous.
"""

    return prompt.strip()

# -------------------------------
# Main extractor function
# -------------------------------

def extract_invoice_from_ocr(ocr_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calls GPT-4o (or 4o-mini) to parse OCR result into structured invoice JSON.
    """
    user_prompt = build_extractor_prompt(ocr_result)

    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",   # you can switch to "gpt-4o" if you want
        messages=[
            {"role": "system", "content": EXTRACTOR_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        # Fallback: if something went wrong, wrap in a dict
        data = {"parse_error": "Invalid JSON from model", "raw": content}

    return data

# -------------------------------
# Quick test hook
# -------------------------------

if __name__ == "__main__":
    from Azure_invoice_ocr import azure_extract_invoice  # your Azure/GPT OCR module

    sample_pdf = r"C:\Users\prave\Downloads\Screenshot 2025-12-14 090830.pdf"

    ocr_data = azure_extract_invoice(sample_pdf)
    invoice = extract_invoice_from_ocr(ocr_data)

    print(json.dumps(invoice, indent=2))
