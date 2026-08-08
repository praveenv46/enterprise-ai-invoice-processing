# agents/azure_invoice_ocr.py

import os
from dotenv import load_dotenv
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential

load_dotenv()

azure_endpoint = os.getenv("AZURE_FORMREC_ENDPOINT")
azure_key = os.getenv("AZURE_FORMREC_KEY")


azure_client = DocumentAnalysisClient(
    endpoint=azure_endpoint,
    credential=AzureKeyCredential(azure_key)
)

def azure_extract_invoice(file_path: str) -> dict:
    """
    Azure OCR for PDF invoices.
    Returns normalized OCR structure:
    {
        full_text,
        pages[],
        tables[][]
    }
    """
    result = {
        "full_text": "",
        "pages": [],
        "tables": []
    }

    with open(file_path, "rb") as f:
        document_bytes = f.read()

    poller = azure_client.begin_analyze_document(
        "prebuilt-invoice",
        document=document_bytes
    )
    doc = poller.result()

    # Text
    for page in doc.pages:
        page_text = "\n".join(line.content for line in page.lines)
        result["pages"].append(page_text)
        result["full_text"] += page_text + "\n"

    # Tables
    for table in doc.tables:
        structured_table = []
        max_row = max(cell.row_index for cell in table.cells)

        for r in range(max_row + 1):
            row_cells = [
                cell for cell in table.cells if cell.row_index == r
            ]
            row_cells = sorted(row_cells, key=lambda c: c.column_index)
            structured_table.append([cell.content for cell in row_cells])

        result["tables"].append(structured_table)

    return result
