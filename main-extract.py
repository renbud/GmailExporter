import base64
import email
import os
from datetime import datetime, timezone
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

GMAIL_USER = "rmbuda@gmail.com"
EXPORT_ROOT = r"D:\\GmailExportedFiles"
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def gmail_service():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
        creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)


def clean_filename(s):
    return "".join(c for c in s if c.isalnum() or c in ("-", "_")).strip()


def get_latest_export_timestamp():
    if not os.path.exists(EXPORT_ROOT):
        return datetime(1970, 1, 1, tzinfo=timezone.utc)

    timestamps = []
    for name in os.listdir(EXPORT_ROOT):
        try:
            ts = name.split("__")[0]
            dt = datetime.strptime(ts, "%Y-%m-%d_%H-%M-%S").replace(tzinfo=timezone.utc)
            timestamps.append(dt)
        except Exception:
            continue

    return max(timestamps) if timestamps else datetime(1970, 1, 1, tzinfo=timezone.utc)


def save_email(service, msg_id):
    msg = service.users().messages().get(userId="me", id=msg_id, format="raw").execute()
    raw = base64.urlsafe_b64decode(msg["raw"])
    mime_msg = email.message_from_bytes(raw)

    # Parse email date
    date_tuple = email.utils.parsedate_tz(mime_msg["Date"])
    dt = datetime.fromtimestamp(email.utils.mktime_tz(date_tuple), tz=timezone.utc)
    timestamp = dt.strftime("%Y-%m-%d_%H-%M-%S")

    folder_name = f"{timestamp}__msgid_{clean_filename(msg_id)}"
    folder_path = os.path.join(EXPORT_ROOT, folder_name)
    os.makedirs(folder_path, exist_ok=True)

    body_text = []
    attachment_count = 0

    for part in mime_msg.walk():
        content_type = part.get_content_type()
        filename = part.get_filename()

        if filename:  # Attachment
            attachment_count += 1
            filename = clean_filename(filename)
            filepath = os.path.join(folder_path, filename)
            with open(filepath, "wb") as f:
                f.write(part.get_payload(decode=True))

        elif content_type == "text/plain":
            body_text.append(part.get_payload(decode=True).decode(errors="ignore"))

    with open(os.path.join(folder_path, "email.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(body_text))


def main():
    service = gmail_service()
    os.makedirs(EXPORT_ROOT, exist_ok=True)

    pivot_dt = get_latest_export_timestamp()
    pivot_query = f"after:{int(pivot_dt.timestamp())}" if pivot_dt > datetime(1970, 1, 1, tzinfo=timezone.utc) else ""

    print(f"Incremental export : {pivot_query}  {int(pivot_dt.timestamp())}    {pivot_dt.isoformat()}")

    results = service.users().messages().list(
        userId=GMAIL_USER, q=pivot_query, maxResults=500
    ).execute()

    messages = results.get("messages", [])

    while "nextPageToken" in results:
        results = service.users().messages().list(
            userId=GMAIL_USER,
            q=pivot_query,
            maxResults=500,
            pageToken=results["nextPageToken"]
        ).execute()
        messages.extend(results.get("messages", []))

    print(f"Found {len(messages)} new messages")

    for m in messages:
        save_email(service, m["id"])


if __name__ == "__main__":
    main()
