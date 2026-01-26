import os
import requests
import duckdb
import argparse
import logging
import glob
import re
import zipfile
import shutil
from datetime import datetime, timedelta

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("IngestPipeline")

# Constants
AGENCY_ID = 'VBL'
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
RAW_DIR = os.path.join(DATA_DIR, 'raw')
PROCESSED_DIR = os.path.join(DATA_DIR, 'processed')

DATASET_PAGE_URL = "https://data.opentransportdata.swiss/dataset/ist-daten-v2"

# Ensure directories exist
os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

def get_resource_url(target_date: datetime) -> str:
    """
    Scrapes the dataset page to find the CSV URL for the given date.
    Parses the JSON-LD block in the HTML via simple regex/json parsing.
    """
    import json
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        logger.info(f"Fetching dataset page: {DATASET_PAGE_URL}")
        response = requests.get(DATASET_PAGE_URL, headers=headers, timeout=30)
        response.raise_for_status()
        
        matches = re.findall(r'<script type="application/ld\+json">(.*?)</script>', response.text, re.DOTALL)
        if not matches:
             raise ValueError("No JSON-LD block found in HTML")
             
        date_str = target_date.strftime('%Y-%m-%d')
        query_date_str = target_date.strftime('%Y-%m-%d') # Default query
        
        for match in matches:
            try:
                data = json.loads(match)
                graph = data.get('@graph', [data])
                
                for item in graph:
                    distributions = item.get('schema:distribution', [])
                    for dist in distributions:
                        if isinstance(dist, dict):
                            url = dist.get('schema:url')
                            if url and query_date_str in url:
                                return url
            except:
                continue
                
        raise ValueError(f"No resource found for date {query_date_str}")
        
    except Exception as e:
        logger.warning(f"Could not find download URL: {e}")
        return None

def download_file(url: str, target_path: str):
    """Downloads file if it doesn't exist."""
    if os.path.exists(target_path):
        logger.info(f"File {target_path} already exists. Skipping download.")
        return

    logger.info(f"Downloading {url}...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        with requests.get(url, stream=True, headers=headers, timeout=300) as r:
            r.raise_for_status()
            with open(target_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        logger.info("Download complete.")
    except Exception as e:
        logger.error(f"Download failed: {e}")
        if os.path.exists(target_path):
            os.remove(target_path)

def extract_date_from_filename(filename: str) -> str:
    """Extracts date in YYYY-MM-DD format from filename."""
    # Matches YYYY-MM-DD
    match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
    if match:
        return match.group(1)
    # Matches YYYYMMDD
    match = re.search(r'(\d{8})', filename)
    if match:
        d = match.group(1)
        return f"{d[:4]}-{d[4:6]}-{d[6:]}"
    return None

def is_processed(date_str: str) -> bool:
    """Checks if a processed parquet file already exists for this date."""
    expected_file = os.path.join(PROCESSED_DIR, f"{date_str}_vbl.parquet")
    return os.path.exists(expected_file)

def process_csv(csv_path: str, date_str: str):
    """
    Processes a single CSV file (extracted to temp) and saves as Parquet.
    """
    output_path = os.path.join(PROCESSED_DIR, f"{date_str}_vbl.parquet")
    
    if os.path.exists(output_path):
        logger.info(f"Skipping {date_str} (Output exists)")
        return

    logger.info(f"Processing day: {date_str}...")
    
    conn = duckdb.connect(database=':memory:')
    try:
        # SQL with conversions
        # Omitted SLOID because it is inconsistent across files.
        query = f"""
        COPY (
            SELECT 
                strptime(BETRIEBSTAG, '%d.%m.%Y')::DATE AS date,
                FAHRT_BEZEICHNER AS trip_id,
                BETREIBER_ABK AS agency_id,
                LINIEN_ID AS line_id,
                LINIEN_TEXT AS line_name,
                UMLAUF_ID AS block_id,
                VERKEHRSMITTEL_TEXT AS transport_type,
                ZUSATZFAHRT_TF::BOOLEAN AS is_additional,
                FAELLT_AUS_TF::BOOLEAN AS is_cancelled,
                BPUIC AS stop_id_bpuic,
                HALTESTELLEN_NAME AS stop_name,
                -- stop_id_sloid OMITTED due to inconsistency
                try_strptime(ANKUNFTSZEIT, '%d.%m.%Y %H:%M')::TIMESTAMP AS arrival_planned,
                try_strptime(AN_PROGNOSE, '%d.%m.%Y %H:%M:%S')::TIMESTAMP AS arrival_actual,
                AN_PROGNOSE_STATUS AS arrival_status,
                try_strptime(ABFAHRTSZEIT, '%d.%m.%Y %H:%M')::TIMESTAMP AS departure_planned,
                try_strptime(AB_PROGNOSE, '%d.%m.%Y %H:%M:%S')::TIMESTAMP AS departure_actual,
                AB_PROGNOSE_STATUS AS departure_status
            FROM read_csv('{csv_path.replace(os.sep, '/')}', header=True, delim=';', all_varchar=True, ignore_errors=True)
            WHERE BETREIBER_ABK = '{AGENCY_ID}'
        ) TO '{output_path.replace(os.sep, '/')}' (FORMAT PARQUET, COMPRESSION 'ZSTD');
        """
        
        conn.execute(query)
        logger.info(f"Saved: {output_path}")
        
    except Exception as e:
        logger.error(f"Failed to process CSV {csv_path}: {e}")
        # Clean up partial output
        if os.path.exists(output_path):
            os.remove(output_path)
    finally:
        conn.close()
        # No need for manual file removal here, done in caller.

def process_zip_contents(zip_path: str):
    """
    Iterates through all CSVs in a ZIP, extracts them one by one to a temp file,
    and processes them if they are not already processed.
    """
    logger.info(f"Inspecting ZIP: {os.path.basename(zip_path)}")
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            csv_files = [f for f in z.infolist() if f.filename.endswith('.csv')]
            
            if not csv_files:
                logger.warning(f"No CSV files found in {zip_path}")
                return
            
            # Setup temp dir
            temp_dir = os.path.join(DATA_DIR, 'temp_processing')
            os.makedirs(temp_dir, exist_ok=True)
            
            for zip_info in csv_files:
                # 1. Determine Date from Filename
                date_str = extract_date_from_filename(zip_info.filename)
                
                if not date_str:
                    logger.warning(f"Skipping {zip_info.filename} (No date found)")
                    continue
                
                # 2. Check overlap
                if is_processed(date_str):
                    # logger.info(f"Skipping {date_str} (Already Processed)")
                    continue
                
                # 3. Extract and Process
                temp_csv_path = os.path.join(temp_dir, zip_info.filename)
                
                logger.info(f"Extracting {zip_info.filename}...")
                with z.open(zip_info) as source, open(temp_csv_path, "wb") as target:
                    shutil.copyfileobj(source, target)
                
                try:
                    process_csv(temp_csv_path, date_str)
                finally:
                    # Force GC not guaranteed, but closing conn usually enough.
                    # On Windows, need to be sure handle is released.
                    # We can add a retry loop for deletion if paranoid.
                    import time
                    if os.path.exists(temp_csv_path):
                        try:
                            os.remove(temp_csv_path)
                        except PermissionError:
                            logger.warning(f"Could not delete {temp_csv_path} immediately. Retrying...")
                            time.sleep(1)
                            try:
                                os.remove(temp_csv_path)
                            except:
                                logger.error(f"Failed to delete {temp_csv_path} after retry.")
            
            # Remove temp dir
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

    except zipfile.BadZipFile:
        logger.error(f"Invalid ZIP file: {zip_path}")

def main():
    parser = argparse.ArgumentParser(description="Smart VBL Ingest Pipeline")
    parser.add_argument('--download', action='store_true', help="Attempt to download yesterday's data")
    args = parser.parse_args()

    # 1. Optional Download
    if args.download:
        yesterday = datetime.now() - timedelta(days=1)
        url = get_resource_url(yesterday)
        
        if url:
            filename = f"Input_{yesterday.strftime('%Y-%m-%d')}_IstDaten.zip"
            target_path = os.path.join(RAW_DIR, filename)
            download_file(url, target_path)
        else:
            logger.info("No URL found for yesterday (or download disabled/failed). Proceeding with local files.")

    # 2. Iterate Raw Directory
    raw_files = glob.glob(os.path.join(RAW_DIR, '*.zip'))
    
    logger.info(f"Found {len(raw_files)} ZIP files in {RAW_DIR}")

    for file_path in raw_files:
        process_zip_contents(file_path)

    logger.info("Pipeline finished.")

if __name__ == "__main__":
    main()
