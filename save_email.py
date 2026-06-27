import base64
import email
import html2text
import logging
import random
import time
import os
from datetime import datetime, timezone

from googleapiclient.errors import HttpError


MAX_FILENAME_LEN = 120

def clean_filename(s: str) -> str:
    if not s:
        return "attachment"

    # Strip weird quotes
    s = s.strip().strip("'").strip('"')

    # Separate extension early
    base, ext = os.path.splitext(s)

    # Clean base + ext separately
    base = "".join(c for c in base if c.isalnum() or c in ("-", "_"))
    ext = "".join(c for c in ext if c.isalnum() or c in (".", "-", "_"))

    if not base:
        base = "attachment"

    # Enforce max length on base only, keep extension
    if len(base) > MAX_FILENAME_LEN:
        base = base[:MAX_FILENAME_LEN]

    return (base + ext).strip()


def gmail_get_with_retry(service, msg_id: str, gmail_user: str, max_retries=7):
    for attempt in range(max_retries):
        try:
            return service.users().messages().get(
                userId= gmail_user,
                id=msg_id,
                format="raw"
            ).execute()

        except (ConnectionResetError, OSError) as e:
            # Network-level failure
            wait = 2 ** attempt + random.random()
            logging.debug(f"Network error on message {msg_id}: {e}. Retrying in {wait:.1f}s")
            time.sleep(wait)

        except HttpError as e:
            # Gmail throttling or backend hiccup
            if e.resp.status in (429, 500, 502, 503, 504):
                wait = 2 ** attempt + random.random()
                logging.debug(f"HTTP {e.resp.status} on message {msg_id}. Retrying in {wait:.1f}s")
                time.sleep(wait)
            else:
                raise  # real error, not retryable

    raise RuntimeError(f"Failed to fetch message {msg_id} after {max_retries} retries")


def save_email(service, msg_id: str, export_root: str, gmail_user: str) -> datetime: 
    msg = gmail_get_with_retry(service, msg_id, gmail_user=gmail_user)
    raw = base64.urlsafe_b64decode(msg["raw"])
    mime_msg = email.message_from_bytes(raw)

    # Parse email date
    date_tuple = email.utils.parsedate_tz(mime_msg["Date"])
    dt = datetime.fromtimestamp(email.utils.mktime_tz(date_tuple), tz=timezone.utc)
    year = dt.strftime("%Y")
    month = dt.strftime("%m")
    day = dt.strftime("%d")

    folder_name = f"{day}__msgid_{clean_filename(msg_id)}"
    folder_path = os.path.join(export_root, year, month, folder_name)

    os.makedirs(folder_path, exist_ok=True)

    # Preserve timestamp on folder
    epoch = dt.timestamp()
    os.utime(folder_path, (epoch, epoch))

    # Extract headers
    hdr_from = mime_msg.get("From", "")
    hdr_to = mime_msg.get("To", "")
    hdr_cc = mime_msg.get("Cc", "")
    hdr_subject = mime_msg.get("Subject", "")
    hdr_date = mime_msg.get("Date", "")
    hdr_msgid = mime_msg.get("Message-ID", "")

    # Extract body + attachments
    body_text = []
    for part in mime_msg.walk():
        content_type = part.get_content_type()
        filename = part.get_filename()

        if filename:  # Attachment
            filename = clean_filename(filename)
            filepath = os.path.join(folder_path, filename)
            # TODO send the filecontents to converters to extract markdown
            # TODO and append markdown to main output md
            with open(filepath, "wb") as f:
                try:
                    f.write(part.get_payload(decode=True))
                    os.utime(filepath, (epoch, epoch))
                except Exception as e:
                    logging.error(f"Error occurred while writing attachment {filename}: {e}")

        elif content_type == "text/plain":
            body_text.append(part.get_payload(decode=True).decode(errors="ignore"))

        elif content_type == "text/html":
            html = part.get_payload(decode=True).decode(errors="ignore")
            # Convert HTML → plain text
            text = html2text.html2text(html)
            body_text.append(text)

    # Write .eml-like file
    # TODO: Change this to markdown and add the markdown from the attachments
    # TODO: Use email-{safe_name(hdr_subject)}.md as filename
    eml_path = os.path.join(folder_path, "email.eml")
    with open(eml_path, "w", encoding="utf-8") as f:
        f.write(f"From: {hdr_from}\n")
        f.write(f"To: {hdr_to}\n")
        if hdr_cc:
            f.write(f"Cc: {hdr_cc}\n")
        f.write(f"Subject: {hdr_subject}\n")
        f.write(f"Date: {hdr_date}\n")
        f.write(f"Message-ID: {hdr_msgid}\n")
        f.write("\n")
        f.write("------------------------------------------------------------\n")
        f.write("BODY (text/plain)\n")
        f.write("------------------------------------------------------------\n\n")
        f.write("\n".join(body_text))

    # Set both access and modification time
    os.utime(eml_path, (epoch, epoch))
    return dt
