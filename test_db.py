import sys
import os
import logging
import json

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import get_punctuality_stats

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestDB")

def test_stats():
    # Use the date we know exists
    date_test = "2025-12-17"
    
    logger.info(f"Testing punctuality stats for {date_test}...")
    stats = get_punctuality_stats(date_test, date_test)
    
    print(json.dumps(stats, indent=2))
    
    if stats['total'] > 0:
        logger.info("SUCCESS: Stats returned data.")
    else:
        logger.error("FAILURE: No data returned.")

if __name__ == "__main__":
    test_stats()
