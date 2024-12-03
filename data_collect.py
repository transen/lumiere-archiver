import requests
import hashlib
import os
import logging
import json
import ijson
from datetime import datetime
from pathlib import Path

# Get the directory where the script is located
SCRIPT_DIR = Path(__file__).resolve().parent

# Define the storage directory relative to the script's directory
STORAGE_DIR = SCRIPT_DIR / "archive"

# Create the directory if it doesn't exist
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


DATA_API_URL = "https://lumierevod.obs.coe.int/api/works"
COUNTRY_CODE_API_URL = "https://lumierevod.obs.coe.int/api/countries"

LAST_CHECKSUM_FILE = SCRIPT_DIR / "last_checksum.txt"
ARCHIVE_FILENAME_PREFIX = "Complete_lumiere_COE_"


# Setup logging
logging.basicConfig(
    filename="data_archive.log",
    level=logging.INFO, # CHANGE INFO TO DEBUG TO GET MORE DETAILED LOGS
    format="%(asctime)s - %(levelname)s - %(message)s"
)


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
            logging.info(f"New datadump downloaded to {new_path}. Checksum: {current_checksum}")


    except Exception as e:
        logging.error(f"Error occurred: {e}")

if __name__ == "__main__":
    main()
