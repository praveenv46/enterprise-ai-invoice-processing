import re
from typing import List, Dict
from openai import OpenAI
import os
import openai
from email_agent import fetch_email
import pdfplumber

llm_enabled = True  # Set to True to enable LLM classification
openai.api_key = os.getenv("OPENAI_API_KEY")
openai_client = openai # Pass a valid OpenAI client object if using LL

def extract_po_number(text: str) -> str:
    """
    Extract PO number using flexible pattern like PO#123,P#123, etc.    
    """
    patterns = [
        r'\bPO[#_\-\s]?(\d+)',   # PO#123, PO-123, PO_123
        r'\bP[#_\-\s]?(\d+)',
        r'\bPurchase\s+Order[:#\s\-]*?(\d+)',
    ]
    for pattern in patterns:
        match = re.search(pattern,text, re.IGNORECASE)
        if match:
            return f"PO{match.group(1)}" 
    
    return None

def extract_po_from_file(pdf_path):
    try:
        with pdfplumber.open(pdf_path) as pdf:
            full_text= ""
            for page in pdf.pages:
                full_text += page.extract_text() or ""
            full_text = extract_po_number(full_text)
            return full_text
    except Exception as e:
        print(f"Error reading {pdf_path}: {e}")
        return None


def classify_type(file_name: str, subject_line: str) -> str:
    """
    Classify the document type based on keyword in filename or subject line.
    """
    combined = f"{file_name}{subject_line}".lower()
    if "invoice" in combined:
        return "Invoice"
    elif "goods receipt" in combined or "grn" in combined:
        return "GRN"
    elif "purchase order" in combined or re.search(r'\bpo\b', combined):
        return "PO"
    else:
        return "Unknown"

def classify_type_llm(file_name: str, subject_line: str, sender : str, openai_client = None):
    prompt = f"""
    You are a smart document classififer.
    Given the following email metadata, identify the document type(Invoice, PO, GRN, Unknown)
    Sender: {sender}
    Subject : {subject_line}
    File Name: {file_name}

    Retrun only one of these type: Invoice, PO, GRN, Unknown
    
    """
    if openai_client:
        response = openai.chat.completions.create(
            model = "gpt-4",
            messages =[{"role":"user","content":prompt }],
            temperature = 0
        )
        return response.choices[0].message.content.strip()
    return "Unknown"

def classify_documents(files: List[Dict]) -> List[Dict]:
    """
    Classify documents and extract PO number from metadata.

    Input:
        List of dicts with 'file_path', 'file_name', 'subject_line'
    
    Output:
        Same list enriched with 'doc_type' and 'po_number'
    """
    results= []
    for f in files:
        file_name = f.get('file_name','')
        subject = f.get('subject_line','')
        sender = f.get('sender','')
        path =f.get('file_path','')
        po_number = extract_po_number(file_name) or extract_po_number(subject) or extract_po_from_file(path)
        doc_type = classify_type(file_name, subject)
        if llm_enabled:
            doc_type = classify_type_llm(file_name, subject, sender, openai_client)  
        results.append({
            "file_path": path,
            "file_name": file_name,
            "subject_line": subject, 
            "doc_type": doc_type,
            "po_number": po_number,
            "sender": sender
        })
          
    return results

if __name__ == "__main__":
    email_attachment = fetch_email()
    result = classify_documents(email_attachment)
    for r in result:
        print(r)

