# LUMIERE VOD ARCHIVER

This is a simple "set and forget"-script that can be set up to run independently to archive the LUMIERE VoD database by the European Audiovisual Observatory, through e.g. chronjobs.


### OBS: This downloads the entire database each time it is run: please don't run it unnecessarily often. LUMIERE VoD has historically predominantly published new datasets 3-4 times a year. Running this once a month will surely suffice.


## Instructions
#TODO: Explain how this works :-) 



Crontab -e

## Planned development: 
Set up external service to be notified of errors and new datasets.


***

# LUMIERE VOD ARCHIVER

This script downloads the latest dataset from the [Lumiere VoD](https://lumierevod.obs.coe.int), which is a database of European (film and TV season) works available on on-demand services active in the European Union and Europe, throughts its [API](https://lumierevod.obs.coe.int/schema/redoc), and archives it to a specified directory, while also checking for any new datasets based on MD5 checksums. It runs as a cron job to automate the monthly check for and download of new data.

## Requirements

Before running this script, ensure you have the following dependencies installed:

- Python 3.6+
- Requests library
- ijson library


## Setup Instructions

1. **Clone the Repository**
Clone this script into your desired directory on your server:

```git clone https://github.com/transen/lumiere-archiver.git lumiere-archiver```
```cd lumiere-archiver```

2. **Setting up a Virtual Environment**

It is highly recommended to use a virtual environment to isolate dependencies for this script. Follow these steps to set it up:

2.1. **Create a virtual environment**:
   Navigate to the directory where you want the script to reside and run:
   ```python -m venv .lumiere-venv```

2.2. **Activate the virtual environment**
- macOS/Linux:
```source .lumiere-venv/bin/activate```
- Windows:
```.lumiere-venv\Scripts\activate```

2.3. **Install the required libraries (with the virtual envionment active) using pip and the included requirements file:**
```pip install -r requirements.txt```


3. **Set up the Cron Job**
To automate the running of this script, set up a cron job that executes the script monthly.
Open the crontab editor:
`crontab -e`
Add a new cron job entry that runs the script every month. For example, to run it at 2:00 AM on the 1st day of every month:
`0 2 1 * * /path/to/venv/bin/python /path/to/lumiere-archiver/data_collect.py`

Adjust the paths accordingly:

- Replace `/path/to/venv/bin/python` with the path to the Python executable in your virtual environment (e.g., /path/to/.lumiere-venv/bin/python3).
- Replace `/path/to/lumiere-dataset-archiver/script.py` with the path to the script.

## Functionality
**Logging**
The script logs information and errors to a file named archiver.log. You can adjust the logging level in the script (currently set to INFO, set to DEBUG for more detailed logging).

**Checksum Tracking**
The script checks for changes in the dataset by comparing the MD5 checksums of the downloaded file with the last recorded checksum. If a new dataset is detected, it is saved with a unique filename based on the presence_date.

**Storage Directory** 
The script saves datasets in the archive/ directory within the script’s folder.

**Script Functionality**
Retrieve Country Codes: Fetches a list of countries from the Lumiere VoD API that are members of the CoE (Council of Europe).
Download Dataset: Downloads the latest dataset for countries in the COE using the Lumiere VoD API. The data is streamed and saved incrementally to avoid excessive memory use.
Checksum Validation: Compares the checksum of the newly downloaded dataset with the last known checksum to determine if the dataset has changed.
File Archiving: If the dataset is new, it is renamed to include the presence_date and stored in the archive/ directory. If the dataset already exists, it is discarded.
Logging: All actions are logged.

**Modifications**
If needed, you can modify the following constants in the `data_collect.py` file:

`DATA_API_URL`: The URL for retrieving dataset data.
`COUNTRY_CODE_API_URL`: The URL for retrieving the list of country codes.
`STORAGE_DIR`: The directory where datasets are saved.
`LAST_CHECKSUM_FILE`: The file where the last checksum is stored.
`ARCHIVE_FILENAME_PREFIX`: The prefix used for archived filenames.


## Keep in mind
This downloads the entire database each time it is run: please do not run it unnecessarily often. LUMIERE VoD has historically published new datasets 3-4 times a year. Running this once a month will surely suffice.

If you experience issues with large datasets, slow downloads or running out of memory, consider adjusting the chunk size for downloading the data. 

If you experience issues with the cronjob, check the time and timezone on your server (conffirm with the `date`-command).


## License
This script is provided under the MIT License, and created at Aarhus University as part of the EUVoD project.   