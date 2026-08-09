# orchestrator.py

import os
from storage_agent import (
    init_db,
    insert_document,
    insert_ocr_result,
    insert_extracted_invoice,
    insert_validated_invoice,
    log_event,
)
from Azure_invoice_ocr import azure_extract_invoice
from extractor_agent import extract_invoice_from_ocr
from validator_agent import validate_invoice


def process_invoice(file_path: str) -> dict:
    """
    End-to-end invoice processing pipeline.
    This is the SINGLE entry point you should run.
    """

    # --------------------------------------------------
    # 0. Initialize DB (idempotent)
    # --------------------------------------------------
    init_db()

    # --------------------------------------------------
    # 1. Read file
    # --------------------------------------------------
    with open(file_path, "rb") as f:
        file_bytes = f.read()

    file_name = os.path.basename(file_path)

    # --------------------------------------------------
    # 2. Register document (hash-based)
    # --------------------------------------------------
    document_id = insert_document(
        file_name=file_name,
        file_bytes=file_bytes,
        doc_type="invoice"
    )

    log_event(document_id, "DOCUMENT_RECEIVED", f"Received file {file_name}")

    # --------------------------------------------------
    # 3. OCR (runs only once per document hash)
    # --------------------------------------------------
    ocr_result = azure_extract_invoice(file_path)

    insert_ocr_result(
        document_id=document_id,
        ocr_provider="AZURE_DOCUMENT_INTELLIGENCE",
        raw_text=ocr_result["full_text"],
        tables=ocr_result.get("tables", [])
    )

    log_event(document_id, "OCR_COMPLETED", "OCR completed using Azure")

    # --------------------------------------------------
    # 4. Extraction
    # --------------------------------------------------
    extracted_invoice = extract_invoice_from_ocr(ocr_result)

    insert_extracted_invoice(
        document_id=document_id,
        extracted_json=extracted_invoice,
        extractor_version="invoice_extractor_v1"
    )

    log_event(document_id, "EXTRACTION_COMPLETED", "Invoice fields extracted")

    # --------------------------------------------------
    # 5. Validation
    # --------------------------------------------------
    validation_result = validate_invoice(extracted_invoice)

    insert_validated_invoice(
        document_id=document_id,
        validated_json=validation_result["validated_invoice"],
        issues=validation_result["issues"],
        is_valid=validation_result["is_valid"]
    )

    log_event(
        document_id,
        "VALIDATION_COMPLETED",
        "Invoice validated successfully" if validation_result["is_valid"] else "Invoice validation failed"
    )

    # --------------------------------------------------
    # 6. Return final result
    # --------------------------------------------------
    return validation_result


# ------------------------------------------------------
# Manual test runner
# ------------------------------------------------------
if __name__ == "__main__":
    file_path = r"C:\Users\prave\Downloads\Screenshot 2025-12-14 090830.pdf"
    result = process_invoice(file_path)
    print(result)
