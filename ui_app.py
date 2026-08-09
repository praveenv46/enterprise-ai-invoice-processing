import streamlit as st
import sqlite3
import json
import os

# ======================================================
# CONFIG
# ======================================================
st.set_page_config(page_title="Invoice Validation Dashboard", layout="wide")

DB_PATH = r"invoice_pipeline.db"

# ======================================================
# SAFETY CHECKS
# ======================================================
if not os.path.exists(DB_PATH):
    st.error(f"❌ Database not found: {DB_PATH}")
    st.stop()

if os.path.getsize(DB_PATH) == 0:
    st.error("❌ Database exists but is EMPTY")
    st.stop()


# ======================================================
# DB HELPERS
# ======================================================
def get_connection():
    return sqlite3.connect(DB_PATH)


def fetch_overview_stats():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM documents")
    total = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM documents WHERE status='VALIDATED'")
    validated = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM documents WHERE status='FAILED'")
    failed = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM documents WHERE status='RECEIVED'")
    pending = cur.fetchone()[0]

    conn.close()
    return total, validated, failed, pending


def fetch_invoice_list():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, file_name, doc_type, status
        FROM documents
        ORDER BY received_at DESC
    """)

    rows = cur.fetchall()
    conn.close()
    return rows


def fetch_validated_invoice(document_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT validated_json, issues_json, is_valid
        FROM validated_invoices
        WHERE document_id = ?
    """, (document_id,))

    row = cur.fetchone()
    conn.close()

    if not row:
        return None

    return {
        "invoice_data": json.loads(row[0]),
        "validation_issues": json.loads(row[1]) if row[1] else [],
        "is_valid": bool(row[2])
    }


def update_invoice_status(document_id, new_status):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE documents
        SET status = ?
        WHERE id = ?
    """, (new_status, document_id))

    conn.commit()
    conn.close()


# ======================================================
# UI HELPERS (A, B)
# ======================================================
def render_validation_message(msg: str):
    msg_lower = msg.lower()

    if "matches" in msg_lower or "validated" in msg_lower:
        st.success(msg)
    elif "informational" in msg_lower or "assumption" in msg_lower:
        st.warning(msg)
    else:
        st.error(msg)


def render_invoice_verdict(validation_issues):
    errors = [i for i in validation_issues if "mismatch" in i.lower()]
    warnings = [i for i in validation_issues if "informational" in i.lower()]

    if errors:
        st.error("❌ Invoice has validation errors. Review required.")
    elif warnings:
        st.warning("⚠️ Invoice is valid with assumptions. Review recommended.")
    else:
        st.success("✅ Invoice is fully validated and ready for approval.")


# ======================================================
# DASHBOARD
# ======================================================
st.title("📄 Invoice Validation Dashboard")

total, validated, failed, pending = fetch_overview_stats()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Invoices", total)
c2.metric("Validated", validated)
c3.metric("Failed", failed)
c4.metric("Pending", pending)

st.divider()

# ======================================================
# INBOX
# ======================================================
st.subheader("📥 Invoice Inbox")

invoice_rows = fetch_invoice_list()

if not invoice_rows:
    st.info("No invoices found.")
    st.stop()

invoice_map = {
    f"{row[1]} | {row[2]} | {row[3]}": row[0]
    for row in invoice_rows
}

selected_label = st.selectbox(
    "Select an invoice to view details",
    invoice_map.keys()
)

selected_doc_id = invoice_map[selected_label]

st.divider()

# ======================================================
# INVOICE DETAIL
# ======================================================
invoice = fetch_validated_invoice(selected_doc_id)

if not invoice:
    st.warning("⚠️ This document has not been validated yet.")
    st.stop()

st.subheader("📄 Invoice Detail")

# B️⃣ Human-readable verdict
render_invoice_verdict(invoice["validation_issues"])

left, right = st.columns(2)

# C️⃣ Extracted JSON (hidden by default)
with left:
    st.markdown("### Extracted Invoice Data")
    with st.expander("🔍 View extracted invoice data (JSON)"):
        st.json(invoice["invoice_data"])

# A️⃣ Color-coded validation issues
with right:
    st.markdown("### Validation Results")
    if not invoice["validation_issues"]:
        st.success("No validation issues found.")
    else:
        for issue in invoice["validation_issues"]:
            render_validation_message(issue)

# ======================================================
# ACTIONS (D)
# ======================================================
st.divider()
st.markdown("### Actions")

a1, a2 = st.columns(2)

with a1:
    if st.button("✅ Approve Invoice"):
        update_invoice_status(selected_doc_id, "APPROVED")
        st.success("Invoice approved.")
        st.experimental_rerun()

with a2:
    if st.button("❌ Reject Invoice"):
        update_invoice_status(selected_doc_id, "REJECTED")
        st.error("Invoice rejected.")
        st.experimental_rerun()
