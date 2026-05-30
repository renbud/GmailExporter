# **GmailExporter – Incremental Gmail to Plain‑Text Exporter**

GmailExporter is a Python tool that exports your Gmail messages into **plain‑text files**, with **attachments saved separately**, using a **safe incremental workflow**.  
Each run exports only *new* emails based on the latest timestamp already present in the export folder.

---

## **Features**

- Exports each email into its own folder  
- Saves the email body as `email.txt`  
- Saves attachments as separate files  
- Uses the email’s own **Date** header for naming  
- Incremental: only exports messages **newer than the latest exported email**  
- Restart‑safe and scalable to tens of thousands of messages  
- Uses the official Gmail API (fast, reliable, structured)

---

## **Folder Structure**

```
gmail_export/
    2024-11-03_14-22-55__msgid_abc123/
        email.txt
        attachment_01.pdf
        attachment_02.png
```

Naming format:

```
YYYY-MM-DD_HH-MM-SS__msgid_<gmail_message_id>
```

This ensures chronological sorting and uniqueness.

---

## **Installation**

Install dependencies using `uv`:

```
uv add google-auth
uv add google-auth-oauthlib
uv add google-api-python-client
```

Or using pip:

```
pip install google-auth google-auth-oauthlib google-api-python-client
```

Place your Google OAuth credentials file in the project directory:

```
credentials.json
```

The script will generate `token.json` on first run.

---

## **Authentication**

The first time you run the exporter:

1. A browser window opens  
2. Log in with your Google account  
3. Approve Gmail read‑only access  
4. A `token.json` file is created for future runs  

---

## **How Incremental Export Works**

1. The exporter scans the `gmail_export/` folder  
2. It finds the **latest timestamp** from previously exported emails  
3. It queries Gmail for messages **after that timestamp**  
4. Only new messages are downloaded  
5. Next run: only newer messages are exported again

This makes the exporter safe to run daily, hourly, or in cron.

---

## **Running the Exporter**

```
python export_gmail.py
```

On first run, it exports your entire mailbox.  
Subsequent runs export only new messages.

---

## **Requirements**

- Python 3.9+  
- A Google account  
- Gmail API enabled in Google Cloud Console  
- `credentials.json` OAuth client file  

---

## **Notes**

- The exporter uses Gmail’s `after:<unix_timestamp>` search query for speed  
- Attachments are saved exactly as provided by Gmail  
- Only `text/plain` parts are written to `email.txt`  
- HTML export can be added if needed  

### Client secrets First Time
1. Go to Google Cloud Console
Open:

https://console.cloud.google.com/apis/credentials (console.cloud.google.com in Bing)

2. Create OAuth Client Credentials
Click Create Credentials

Choose OAuth client ID

Application type: Desktop app

Download the JSON file

Google will give you a file named something like:

Code
client_secret_1234567890abcdef.json
3. Rename it to exactly:
Code
credentials.json
4. Place it here:
Code
D:\GmailExporter\credentials.json