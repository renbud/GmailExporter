# GmailExporter – Incremental Gmail to EML Files Exporter
* Uses Google API
* Authenticates with registered Google OAuth credentials
* Exports all labels from Gmail
* Saves both text and HTML versions of emails in an .eml file
* Saves attachments as separate files
* Files are back-dated to the time of the email
* Handles incremental exports using pivot.json to track the latest exported message
* Can be used as an archive or input to an indexing system

## Requirements

- Python 3.9+
- A Google account
- Gmail API enabled in Google Cloud Console
- credentials.json OAuth client file (see how to create it below)

## Folder Structure

```
gmail_export/
    YY
        MM
            DD_msgid_abc123/
                email.eml
                attachment_01.pdf
                attachment_02.png
```

This ensures chronological sorting and uniqueness.

## Installation

Install dependencies:

```bash
uv sync
```

## Configure

1. Copy `config/config.yaml.template` to `config/config.yaml`
2. Edit `config/config.yaml`:
   - Set `export_root:` to your desired folder path
   - Set `gmail_user:` to your Gmail account name
3. Place `credentials.json` in the project root directory
### Credentials.json First Time

1. Go to Google Cloud Console
Open: https://console.cloud.google.com/apis/credentials (console.cloud.google.com in Bing)

2. Create OAuth Client Credentials
Click Create Credentials

3. Choose OAuth client ID
Application type: Desktop app
Download the JSON file
Google will give you a file named something like:

```json
client_secret_1234567890abcdef.json
```

4. Rename it to exactly `credentials.json` and move to the app folder

## Running the Exporter

```bash
uv run python main.py
```

## Authentication

The first time you run the exporter:

1. A browser window opens
2. Log in with your Google account
3. Approve Gmail read-only access
4. A token.json file is created for future runs

## How Incremental Export Works
On first run, it exports your entire mailbox and creates pivot.json.
Subsequent runs export only new messages based on the timestamp in pivot.json.

1. The exporter reads pivot.json to find the timestamp of the most recent exported file.
2. It queries Gmail for messages after that timestamp
3. At the end of the run the timestamp of the most recent message is saved in pivot.json
4. If you want to re-extract all from scratch remove pivot.json

This makes the exporter safe to run daily, hourly, or in cron.
