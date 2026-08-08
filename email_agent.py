import imaplib
import email
import os
import re
from email.header import decode_header
from dotenv import load_dotenv

#Load Credential
load_dotenv()
EMAIL_USER = os.environ.get("EMAIL_USER") 
EMAIL_PASS = os.environ.get("EMAIL_PASS")
EMAIL_HOST = os.environ.get("EMAIL_HOST", "imap.gmail.com").strip()


#To check and create Output directory
ATTACHMENT_DIR = r"C:\Users\prave\Desktop\AI\3 Way matching\Emails"
os.makedirs(ATTACHMENT_DIR, exist_ok=True)

#Keyword to match in the Subject
KEYWORD = ["PO","Invoice", "Goods Receipt","Purchase Order", "Inv#"]

def Clean(text):
    cleaned_text = ""
    for character in text:
        if character.isalnum():
            cleaned_text += character
        else:
            cleaned_text +="-"
    return cleaned_text

def connect_imap():
    try:
        imap_port = 993
        if not EMAIL_USER or not EMAIL_PASS or not EMAIL_HOST:
            raise ValueError("Missing one or more required environment variables.")

        print(f"Connecting to {EMAIL_HOST}:{imap_port} as {EMAIL_USER}")
        print(f"EMAIL_HOST: [{EMAIL_HOST}]")

        mail = imaplib.IMAP4_SSL(EMAIL_HOST, imap_port)
        mail.login(EMAIL_USER, EMAIL_PASS)
        print("✅ IMAP connection successful")
        return mail
    except Exception as e:
        print(f"❌ IMAP connection failed: {e}")
        return None

def fetch_email():
    mail = connect_imap()
    if mail is None:
        return []
    mail.select("Inbox")

    result,data = mail.search(None, "UNSEEN")
    email_ids = data[0].split()
    attachments = []

    for eid in reversed(email_ids):
        result, data = mail.fetch(eid, "(RFC822)")
        raw_email = data[0][1]
        msg = email.message_from_bytes(raw_email)

        subject, encoding = decode_header(msg["Subject"])[0]
        if isinstance(subject, bytes):
            subject = subject.decode(encoding or "utf-8", errors="ignore")

        subject_lower = subject.lower()
        found_keyword = False
        
        for k in KEYWORD:
            if k.lower() in subject_lower:
                found_keyword =  True
                break
        if found_keyword:
            for part in msg.walk():
                if part.get_content_maintype()=="multipart":
                    continue
                if part.get("Content-Disposition") is None:
                    continue
                
                filename = part.get_filename()
                if filename and filename.lower().endswith(".pdf"):
                    filepath = os.path.join(ATTACHMENT_DIR, Clean(filename))
                    with open(filepath,"wb") as f:
                        f.write(part.get_payload(decode=True))
                    
                    attachments.append({"subject_line":subject, "file_name":Clean(filename),"file_path": filepath,"sender":msg["From"]})

    mail.logout()
    return attachments

if __name__ == "__main__":
    results = fetch_email()
    print ("Download attachment:")
    for item in results:
        print(f"{item['subject_line']} → 📄 {item['file_path']}")
                

