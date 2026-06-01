
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

# Configure logging
def setup_logging(log_level="INFO"):
    """Set up logging configuration from config or default."""
    log_format = "%(asctime)s - %(levelname)s - %(message)s"
    
    if log_level == "DEBUG":
        level = logging.DEBUG
    elif log_level == "WARNING":
        level = logging.WARNING
    elif log_level == "ERROR":
        level = logging.ERROR
    else:
        level = logging.INFO
    
    logging.basicConfig(
        level=level,
        format=log_format,
        datefmt="%Y-%m-%d %H:%M:%S"
    )

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
    """Load gmail_user, export_root, and log_level from config.yaml."""
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

        # Load log_level from config
        log_level = config.get("log_level", "INFO")
        setup_logging(log_level)

        return {
            "gmail_user": config["gmail_user"],
            "export_root": Path(config["export_root"]),
            "filters": config.get("filters", {})
        }

    except FileNotFoundError:
        logging.error("config.yaml not found in current directory.")
        # Use default logging for error case
        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
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
    filters = config.get("filters", {})

    service = gmail_service()
    os.makedirs(EXPORT_ROOT, exist_ok=True)

    pivot_ts = load_pivot()
    
    # Build filters from config
    include = filters.get("include_categories", [])
    exclude = filters.get("exclude_categories", [])
    include_labels = filters.get("include_labels", [])
    exclude_labels = filters.get("exclude_labels", [])
    
    pivot_query = f"after:{pivot_ts}" if pivot_ts > 0 else ""

    # Add category filters
    for cat in include:
        pivot_query += f" category:{cat}"
    for cat in exclude:
        pivot_query += f" -category:{cat}"

    # Add label filters
    for label in include_labels:
        pivot_query += f" label:{label}"
    for label in exclude_labels:
        pivot_query += f" -label:{label}"

    logging.info(f"Incremental export : {pivot_query}")

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

    logging.info(f"Found {len(messages)} new messages")
    
    if messages:
        logging.debug(f"First message: {messages[0]}")

    max_ts = pivot_ts
    for m in messages:
        dt = save_email(service, m["id"], EXPORT_ROOT, GMAIL_USER)
        max_ts = max(max_ts, dt.timestamp())

    save_pivot(max_ts)

if __name__ == "__main__":
    main()
