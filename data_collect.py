import requests
import hashlib
import os
import logging
import json
import ijson
import smtplib
from email.utils import formataddr
from datetime import datetime
from pathlib import Path

# Set up cronjob monitoring with healthchecks.io by flipping the constant below to True, and changing the UUID from None to the UUID as a string 
HEALTHCHECKS_CRON_MONITOR = False # True
HEALTHCHECKS_CRON_UUID = None # "UUID1234"

SMTP_NOTIFICATIONS = False # True
# Email configuration
SMTP_SERVER = None #"smtp.example.com"
SMTP_PORT = None #587
EMAIL_USER = None #"your-email@example.com"
EMAIL_PASS = None #"your-email-password" Depending on your environment it could be good practive to put this in a secrets-file
RECIPIENTS = None #["recipient1@example.com", "recipient2@example.com"]

# Get the directory where the script is located
SCRIPT_DIR = Path(__file__).resolve().parent

# Define the storage directory relative to the script's directory
STORAGE_DIR = SCRIPT_DIR / "archive"

# Create the directory if it doesn't exist
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# Lumiere VoD API endpoints
DATA_API_URL = "https://lumierevod.obs.coe.int/api/works"
COUNTRY_CODE_API_URL = "https://lumierevod.obs.coe.int/api/countries"

LAST_CHECKSUM_FILE = SCRIPT_DIR / "last_checksum.txt"
LOG_FILE = SCRIPT_DIR / "archive.log"
ARCHIVE_FILENAME_PREFIX = "Complete_lumiere_COE_"


# Setup logging
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO, # CHANGE INFO TO DEBUG TO GET MORE DETAILED LOGS
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def send_email(subject, message):
    """
    Sends a plain-text email using smtplib.
    
    Args:
        subject (str): The subject of the email.
        message (str): The plain-text message body.
    """
    try:
        # Set up the SMTP server and start TLS encryption

        # Initialize SMTP connection
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            #server.starttls()  # Upgrade connection to secure # OBS disable this if needed

            # Log in to the SMTP server
            server.login(EMAIL_USER, EMAIL_PASS)

            # Formatted sender
            formatted_sender = formataddr(('Lumiere Archiver', EMAIL_USER))
            # Construct email header
            header = f'To: {RECIPIENTS}\nFrom: {formatted_sender}\n'

            # Construct the email
            email_body = f"Subject: {subject}\n\n{message}"

            # Send the email
            server.sendmail(from_addr=EMAIL_USER, to_addrs=RECIPIENTS, msg=header+email_body) 
            logging.info(f"Email sent successfully to {RECIPIENTS}")

    except Exception as e:
        logging.critical(f"Failed to send email: {e}")

def retrieve_countrycodes(url):
    # Retrieving a list of countries from Lumiere's own DB    
    payload = {}
    headers = {
        'Accept': 'application/json'
    }
    
    response = requests.request("GET", url, headers=headers, data=payload)
    response.raise_for_status()

    countries = response.json()
    
    # Making a list of countries that is COE
    coe_countries = [country for country in countries if country["is_coe"]]
    
    coe_countrycodes = [country["code"] for country in coe_countries]
    return coe_countrycodes


def download_current_dataset(url, country_codes, destination):
    """
    Download the current dataset using a POST request and save it in chunks to a file.

    Args:
        url (str): The API endpoint.
        country_codes (list): A list of country codes to include in the payload.
        destination (str): The file path where the dataset will be saved.
    """
    # Define the payload for the POST request
    payload = json.dumps({
        "id_type": "",
        "ids": [],
        "title": "",
        "directors": [],
        "work_types": [],
        "production_years": [],
        "production_countries": [],
        "catalogs": [],
        "catalogs_countries": country_codes,
        "business_models": [
            "FoD",
            "SVoD",
            "TVoD",
        ]
    })
    
    # Define headers
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    # Make the POST request
    response = requests.post(url, headers=headers, data=payload, stream=True)
    response.raise_for_status()  # Raise an error for bad responses (4xx, 5xx)

    # Write the response to the destination file in chunks
    with open(destination, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):  # Adjust chunk size as needed
            if chunk:  # Filter out keep-alive chunks
                f.write(chunk)
    
    return


def read_presence_date(file_path):
    with open(file_path, "rb") as file:
        # Use ijson to parse the file incrementally
        parser = ijson.parse(file)
        # Loop through the parsed JSON objects
        for prefix, event, value in parser:
            # We're looking for the presence_date in the given path
            if prefix == "item.presences.item.presence_date":
                return value


def calculate_md5(file_path):
    """Calculate MD5 checksum for a file."""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def generate_unique_filename(base_path: Path, presence_date: str, prefix: str) -> Path:
    """
    Generate a unique filename by appending an increasing integer suffix if the file already exists.

    Args:
        base_path (Path): The directory where the file will be stored.
        presence_date (str): The date to include in the filename.
        prefix (str): The prefix for the filename.

    Returns:
        Path: A unique file path.
    """
    counter = 0
    while True:
        # Generate the filename with or without a suffix
        if counter == 0:
            filename = f"{prefix}{presence_date}.json"
        else:
            filename = f"{prefix}{presence_date}_{counter}.json"
        
        new_path = base_path / filename
        if not new_path.exists():
            return new_path
        counter += 1

def ping_healthchecks_cron(uuid):
    try:
        requests.get(f"https://hc-ping.com/{uuid}", timeout=10)
        logging.info(f"Ping sent to Healthchecks.io UUID {HEALTHCHECKS_CRON_UUID}")
    except requests.RequestException as e:
        logging.critical(f"Cron ping failed: {e}")


def main():
    logging.info("CHECKING FOR NEW DATASETS...")
    try:
        # Create a timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Fetch applicable countrycodes
        coe_countrycodes = retrieve_countrycodes(COUNTRY_CODE_API_URL)
        logging.debug(f"COE countries ({len(coe_countrycodes)}): {coe_countrycodes}")
        
        # Create the destination path
        destination_path = STORAGE_DIR / f"{timestamp}.json"

        logging.info(f"Downloading current dataset as {destination_path}...")

        # Download the most recent dataset
        download_current_dataset(DATA_API_URL, coe_countrycodes, destination_path)

        # Determine the checksum of the newly downloaded dataset
        current_checksum = calculate_md5(destination_path)

        logging.debug(f"Checksum for newly downloaded dataset: {current_checksum}")

        # Check if file is new
        if os.path.exists(LAST_CHECKSUM_FILE):
            with open(LAST_CHECKSUM_FILE, "r") as f:
                last_checksum = f.read().strip()
        else:
            last_checksum = ""
        logging.debug(f"Checksum for existing newest dataset: {last_checksum}")

        # Determine whether a new dataset has been releases (not new if checksums match)
        no_new_dataset = current_checksum == last_checksum

        if no_new_dataset:
            # Log it
            logging.info("Checksums match: no new dataset was released. Removing newly downloaded file...")
            if SMTP_NOTIFICATIONS: send_email(subject="Monthly LumiereVoD check: No new dataset found.", message="Lumiere-archiver checked whether a new dataset has been identified, and it was not.")
            # Remove newly downloaded dataset
            os.remove(destination_path)
        else:
            # Determine presence date
            presence_date = read_presence_date(destination_path)
             # Log it
            logging.info(f"Checksum has changed: a new dataset has been released for {presence_date}!")
            # Determine new filename
            new_path = generate_unique_filename(STORAGE_DIR, presence_date, ARCHIVE_FILENAME_PREFIX)
            #new_path = STORAGE_DIR / f"{ARCHIVE_FILENAME_PREFIX}{presence_date}.json" #TODO: Delete this
            # Adjust filename of dataset
            os.rename(destination_path, new_path)
            # Update the checksum file
            with open(LAST_CHECKSUM_FILE, "w") as f:
                f.write(current_checksum)
            # Final log
            if SMTP_NOTIFICATIONS: send_email(subject="Monthly LumiereVoD check: A new dataset was found!", message=f"Lumiere-archiver checked whether a new dataset has been identified, and it was!\n\nIt was archived as {new_path}")
            logging.info(f"New datadump downloaded to {new_path}. Checksum: {current_checksum}")

        if HEALTHCHECKS_CRON_MONITOR: ping_healthchecks_cron(HEALTHCHECKS_CRON_UUID)

    except Exception as e:
        logging.error(f"Error occurred: {e}")

if __name__ == "__main__":
    main()
