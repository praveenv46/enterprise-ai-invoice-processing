import sqlite3
import json
import hashlib
from datetime import datetime

DB_PATH = r"C:\Users\prave\Desktop\AI\invoice_pipeline.db"

# ======================================================
# Database connection
# ======================================================

def get_connection():
    return sqlite3.connect(DB_PATH)


def now() -> str:
    return datetime.utcnow().isoformat()


def compute_file_hash(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()


# ======================================================
# Database initialization
# ======================================================

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # -------------------------
    # documents (identity)
    # -------------------------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_name TEXT NOT NULL,
        file_hash TEXT NOT NULL UNIQUE,
        doc_type TEXT NOT NULL,
        status TEXT NOT NULL,
        received_at TEXT NOT NULL
    )
    """)

    # -------------------------
    # ocr_results (immutable snapshot)
    # -------------------------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS ocr_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        document_id INTEGER NOT NULL UNIQUE,
        ocr_provider TEXT NOT NULL,
        raw_text TEXT,
        raw_tables_json TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY(document_id) REFERENCES documents(id)
    )
    """)

    # -------------------------
    # extracted_invoices (mutable)
    # -------------------------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS extracted_invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        document_id INTEGER NOT NULL UNIQUE,
        extracted_json TEXT NOT NULL,
        extractor_version TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(document_id) REFERENCES documents(id)
    )
    """)

    # -------------------------
    # validated_invoices (mutable)
    # -------------------------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS validated_invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        document_id INTEGER NOT NULL UNIQUE,
        validated_json TEXT NOT NULL,
        issues_json TEXT,
        is_valid INTEGER NOT NULL,
        validated_at TEXT NOT NULL,
        FOREIGN KEY(document_id) REFERENCES documents(id)
    )
    """)

    # -------------------------
    # processing_events (audit)
    # -------------------------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS processing_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        document_id INTEGER NOT NULL,
        event_type TEXT NOT NULL,
        message TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY(document_id) REFERENCES documents(id)
    )
    """)

    conn.commit()
    conn.close()


# ======================================================
# Insert helpers
# ======================================================

def insert_document(file_name: str, file_bytes: bytes, doc_type: str) -> int:
    file_hash = compute_file_hash(file_bytes)

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    INSERT OR IGNORE INTO documents
        (file_name, file_hash, doc_type, status, received_at)
    VALUES (?, ?, ?, ?, ?)
    """, (file_name, file_hash, doc_type, "RECEIVED", now()))

    conn.commit()

    cur.execute(
        "SELECT id FROM documents WHERE file_hash = ?",
        (file_hash,)
    )
    document_id = cur.fetchone()[0]

    conn.close()
    return document_id


def insert_ocr_result(document_id: int, ocr_provider: str, raw_text: str, tables):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    INSERT OR IGNORE INTO ocr_results
        (document_id, ocr_provider, raw_text, raw_tables_json, created_at)
    VALUES (?, ?, ?, ?, ?)
    """, (
        document_id,
        ocr_provider,
        raw_text,
        json.dumps(tables) if tables else None,
        now()
    ))

    conn.commit()
    conn.close()


def insert_extracted_invoice(document_id: int, extracted_json: dict, extractor_version="v1"):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    INSERT OR REPLACE INTO extracted_invoices
        (document_id, extracted_json, extractor_version, created_at)
    VALUES (?, ?, ?, ?)
    """, (
        document_id,
        json.dumps(extracted_json),
        extractor_version,
        now()
    ))

    conn.commit()
    conn.close()


def insert_validated_invoice(document_id: int, validated_json: dict, issues: list, is_valid: bool):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    INSERT OR REPLACE INTO validated_invoices
        (document_id, validated_json, issues_json, is_valid, validated_at)
    VALUES (?, ?, ?, ?, ?)
    """, (
        document_id,
        json.dumps(validated_json),
        json.dumps(issues),
        int(is_valid),
        now()
    ))

    cur.execute("""
    UPDATE documents
    SET status = ?
    WHERE id = ?
    """, (
        "VALIDATED" if is_valid else "FAILED",
        document_id
    ))

    conn.commit()
    conn.close()


def log_event(document_id: int, event_type: str, message: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO processing_events
        (document_id, event_type, message, created_at)
    VALUES (?, ?, ?, ?)
    """, (
        document_id,
        event_type,
        message,
        now()
    ))

    conn.commit()
    conn.close()


# ======================================================
# Bootstrap
# ======================================================

if __name__ == "__main__":
    init_db()
    print("SQLite database initialized successfully.")
