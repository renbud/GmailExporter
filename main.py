
from importlib.resources import path
import logging
import os
import yaml
from pathlib import Path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from save_email import save_email
from pivot import load_pivot, save_pivot

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



def load_config():
    """Load gmail_user and export_root from config.yaml."""
    config_path = Path("config/config.yaml")

    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        # Validate required keys
        if not isinstance(config, dict):
            logging.error("config.yaml is not a valid YAML mapping.")
            return None

        if "gmail_user" not in config or "export_root" not in config:
            logging.error("config.yaml must contain 'gmail_user' and 'export_root'.")
            return None

        return {
            "gmail_user": config["gmail_user"],
            "export_root": Path(config["export_root"])
        }

    except FileNotFoundError:
        logging.error("config.yaml not found in current directory.")
        return None

    except yaml.YAMLError as e:
        logging.critical(f"Error parsing config.yaml: {e}")
        return None


def main():
    config = load_config()
    if not config:
        logging.critical("Failed to load configuration.")
        return

    GMAIL_USER = config["gmail_user"]
    EXPORT_ROOT = config["export_root"]

    service = gmail_service()
    os.makedirs(EXPORT_ROOT, exist_ok=True)

    pivot_ts = load_pivot()
    pivot_query = f"after:{pivot_ts}" if pivot_ts > 0 else ""

    pivot_query = (
        pivot_query +
        " -category:spam "
        "-category:promotions "
        "-category:social "
        "-category:updates "
        "-category:forums"
    )

    print(f"Incremental export : {pivot_query}")

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
    print(f"First {messages[0]}")

    max_ts = pivot_ts
    for m in messages:
        dt = save_email(service, m["id"], EXPORT_ROOT, GMAIL_USER)
        max_ts = max(max_ts, dt.timestamp())

    save_pivot(max_ts)

if __name__ == "__main__":
    main()
