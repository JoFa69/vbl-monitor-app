import os
import requests
import duckdb
import argparse
import logging
from datetime import datetime, timedelta
import zipfile
import io

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
API_PACKAGE_URL = "https://data.opentransportdata.swiss/api/3/action/package_show?id=ist-daten-v2"
AGENCY_ID = 'VBL'
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
AGENCY_ID = 'VBL'
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
RAW_DIR = os.path.join(DATA_DIR, 'raw')
PROCESSED_DIR = os.path.join(DATA_DIR, 'processed')

def setup_directories():
    os.makedirs(RAW_DIR, exist_ok=True)
    os.makedirs(PROCESSED_DIR, exist_ok=True)

def get_resource_url(target_date: datetime) -> str:
    """
    Scrapes the dataset page to find the CSV URL for the given date.
    Parses the JSON-LD block in the HTML.
    """
    import re
    import json
    
    DATASET_URL = "https://data.opentransportdata.swiss/dataset/ist-daten-v2"
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        logger.info(f"Fetching dataset page: {DATASET_URL}")
        response = requests.get(DATASET_URL, headers=headers)
        response.raise_for_status()
        
        # Regex to find the LD+JSON block
        # Looking for <script type="application/ld+json"> ... </script>
        # Check for multiple blocks? usually one main one for dataset.
        
        matches = re.findall(r'<script type="application/ld\+json">(.*?)</script>', response.text, re.DOTALL)
        
        if not matches:
             raise ValueError("No JSON-LD block found in HTML")
             
        # Parse all found JSON blocks to find the one with distribution/resources
        resource_url = None
        date_str = target_date.strftime('%Y-%m-%d')
        
        for i, match in enumerate(matches):
            try:
                data = json.loads(match)
                if isinstance(data, dict):
                    # Handle graph format
                    graph = data.get('@graph', [])
                    if not graph:
                        # Maybe it is just a single object (Dataset) not in graph?
                        # If so, treat data as a node.
                        graph = [data]
                    
                    # Build ID map
                    node_map = {}
                    for item in graph:
                        if '@id' in item:
                            node_map[item['@id']] = item
                            
                    # Find Dataset node(s) with distributions
                    # Explicitly look for distributions in all nodes, verify against node_map if it's a ref.
                    
                    for item in graph:
                        distributions = item.get('schema:distribution', [])
                        if not distributions:
                            continue
                            
                        for dist in distributions:
                            if not isinstance(dist, dict):
                                continue
                                
                            # Resolve reference if needed
                            dist_node = dist
                            if isinstance(dist, dict) and '@id' in dist:
                                dist_id = dist['@id']
                                if dist_id in node_map:
                                    dist_node = node_map[dist_id]
                            
                            # Now check URL
                            url = dist_node.get('schema:url')
                            name_obj = dist_node.get('schema:name')
                            
                            if url and date_str in url:
                                return url
                            
                            # Check name
                            if isinstance(name_obj, list):
                                for n in name_obj:
                                    if date_str in n.get('@value', ''):
                                       if url:
                                           return url
            except json.JSONDecodeError as e:
                logger.error(f"JSON Decode Error in block {i}: {e}")
                continue
        
        raise ValueError(f"No resource found for date {date_str} in HTML")
        
    except Exception as e:
        logger.error(f"Error scraping resource URL: {e}")
        raise

def download_file(url: str, local_path: str):
    """Downloads a file from URL to local path (streaming)."""
    if os.path.exists(local_path):
        logger.info(f"File {local_path} already exists. Skipping download.")
        return

    logger.info(f"Downloading from {url} to {local_path}...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    with requests.get(url, stream=True, headers=headers) as r:
        r.raise_for_status()
        with open(local_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    logger.info("Download complete.")

def process_data(zip_path: str, date_str: str):
    """
    Uses DuckDB to read the CSV from the ZIP, filter, and save as Parquet.
    """
    logger.info("Processing data with DuckDB...")
    
    # Define output path
    output_path = os.path.join(PROCESSED_DIR, f"{date_str}_vbl.parquet")
    
    # DuckDB SQL Query
    # Note on ZIP reading: DuckDB can read directly from ZIPs usually, 
    # but sometimes unzipping is more robust if the internal structure varies.
    # We will try direct read using 'read_csv' automatically handling compression if extension is .zip?
    # Actually, DuckDB's read_csv automagically handles gzip/zstd but zip might need special handling 
    # or the 'unzip' prefix if httpfs is loaded. 
    # Since we strictly downloaded a file, simplest is to extract it or let DuckDB try.
    # Let's extract to be safe and inspection-friendly if needed, but for speed, direct is better.
    # Given the requirements "Download (Stream)", let's try reading the ZIP directly if possible.
    # If not, we extract.
    
    # Let's assume the ZIP contains exactly one CSV file which is the data.
    try:
        conn = duckdb.connect(database=':memory:')
        
        # Query to Load, Transformation, Filter
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
                SLOID AS stop_id_sloid,
                try_strptime(ANKUNFTSZEIT, '%d.%m.%Y %H:%M')::TIMESTAMP AS arrival_planned,
                try_strptime(AN_PROGNOSE, '%d.%m.%Y %H:%M:%S')::TIMESTAMP AS arrival_actual,
                AN_PROGNOSE_STATUS AS arrival_status,
                try_strptime(ABFAHRTSZEIT, '%d.%m.%Y %H:%M')::TIMESTAMP AS departure_planned,
                try_strptime(AB_PROGNOSE, '%d.%m.%Y %H:%M:%S')::TIMESTAMP AS departure_actual,
                AB_PROGNOSE_STATUS AS departure_status
            FROM read_csv('{zip_path.replace(chr(92), chr(47))}', header=True, all_varchar=True)
            WHERE BETREIBER_ABK = '{AGENCY_ID}'
        ) TO '{output_path.replace(chr(92), chr(47))}' (FORMAT PARQUET, COMPRESSION 'ZSTD');
        """
        
        logger.info("Executing DuckDB Query...")
        conn.execute(query)
        logger.info(f"Saved processed data to {output_path}")
        
        # Verification
        count = conn.execute(f"SELECT COUNT(*) FROM read_parquet('{output_path.replace(chr(92), chr(47))}')").fetchone()[0]
        logger.info(f"Total rows in output: {count}")
        
    except Exception as e:
        logger.error(f"DuckDB processing failed: {e}")
        raise
    finally:
        conn.close()

def main():
    parser = argparse.ArgumentParser(description="Ingest VBL public transport data.")
    parser.add_argument('--date', type=str, help="Date to fetch (YYYY-MM-DD). Defaults to yesterday.")
    args = parser.parse_args()
    
    setup_directories()
    
    # Determine date
    if args.date:
        target_date = datetime.strptime(args.date, '%Y-%m-%d')
    else:
        target_date = datetime.now() - timedelta(days=1)
    
    logger.info(f"Target Date: {target_date.strftime('%Y-%m-%d')}")
    
    # 1. Get URL
    try:
        csv_url = get_resource_url(target_date)
        logger.info(f"Found URL: {csv_url}")
    except ValueError as e:
        logger.error(str(e))
        return

    # 2. Download
    zip_filename = f"raw_{target_date.strftime('%Y%m%d')}.zip"
    zip_path = os.path.join(RAW_DIR, zip_filename)
    
    download_file(csv_url, zip_path)
    
    # 3. Process
    try:
        process_data(zip_path, target_date.strftime('%Y-%m-%d'))
    except Exception as e:
        logger.error("Processing failed.")
        # retain zip for debugging? Or delete?
        import time
        time.sleep(2) # Wait for file lock release
        if os.path.exists(zip_path):
            try:
                os.remove(zip_path)
            except Exception as del_e:
                logger.warning(f"Could not remove temp file: {del_e}")
        return

    # 4. Cleanup
    if os.path.exists(zip_path):
        try:
            import time
            time.sleep(1)
            os.remove(zip_path)
            logger.info("Raw zip file removed.")
        except Exception as e:
            logger.warning(f"Failed to remove temp file: {e}")

if __name__ == "__main__":
    main()
