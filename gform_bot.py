import requests
import random
import time
import argparse
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    handlers=[
        logging.FileHandler("log.txt"),
        logging.StreamHandler()
    ]
)

FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSeXyKpROVhz6hnbLiNWpiSStdk-mGtFUnx9IG-juDXVCzovAg/formResponse"

FIELDS = {
    # Part 1: Sales & Financial Issues
    "entry.1073028820": [1, 2, 3, 4, 5],
    "entry.1534527371": [1, 2, 3, 4, 5],
    "entry.1824670283": [1, 2, 3, 4, 5],
    "entry.2065257654": [1, 2, 3, 4, 5],
    "entry.1958451722": [1, 2, 3, 4, 5],
    # Operational Performance
    "entry.1158536296": [1, 2, 3, 4, 5],
    "entry.1208633648": [1, 2, 3, 4, 5],
    "entry.125228566":  [1, 2, 3, 4, 5],
    "entry.229164637":  [1, 2, 3, 4, 5],
    "entry.931029854":  [1, 2, 3, 4, 5],
    # Marketing Performance
    "entry.838163659":  [1, 2, 3, 4, 5],
    "entry.1981633268": [1, 2, 3, 4, 5],
    "entry.1025240302": [1, 2, 3, 4, 5],
    "entry.2132415631": [1, 2, 3, 4, 5],
    "entry.1395475420": [1, 2, 3, 4, 5],
    # Human Resource Performance
    "entry.1896395260": [1, 2, 3, 4, 5],
    "entry.1604475851": [1, 2, 3, 4, 5],
    "entry.501751395":  [1, 2, 3, 4, 5],
    "entry.1259896805": [1, 2, 3, 4, 5],
    "entry.1911932776": [1, 2, 3, 4, 5],
    # SWOT Assessment
    "entry.2048562672": [1, 2, 3, 4, 5],
    "entry.637855574":  [1, 2, 3, 4, 5],
    "entry.435189453":  [1, 2, 3, 4, 5],
    "entry.2073197847": [1, 2, 3, 4, 5],
    "entry.753148199":  [1, 2, 3, 4, 5],
    
    # Part 2: Functional Suitability
    "entry.1770471280": [1, 2, 3, 4, 5],
    "entry.1306628739": [1, 2, 3, 4, 5],
    "entry.1863604018": [1, 2, 3, 4, 5],
    "entry.1053336508": [1, 2, 3, 4, 5],
    "entry.620134986":  [1, 2, 3, 4, 5],
    # Performance Efficiency
    "entry.1670338690": [1, 2, 3, 4, 5],
    "entry.1457259386": [1, 2, 3, 4, 5],
    "entry.461795711":  [1, 2, 3, 4, 5],
    "entry.486281422":  [1, 2, 3, 4, 5],
    "entry.1193061868": [1, 2, 3, 4, 5],
    # Compatibility
    "entry.509544094":  [1, 2, 3, 4, 5],
    "entry.1867347108": [1, 2, 3, 4, 5],
    "entry.964321943":  [1, 2, 3, 4, 5],
    "entry.610803395":  [1, 2, 3, 4, 5],
    "entry.857113999":  [1, 2, 3, 4, 5],
    # Usability
    "entry.1084420106": [1, 2, 3, 4, 5],
    "entry.989625805":  [1, 2, 3, 4, 5],
    "entry.1933737404": [1, 2, 3, 4, 5],
    "entry.1901357432": [1, 2, 3, 4, 5],
    "entry.723747481":  [1, 2, 3, 4, 5],
    # Security
    "entry.1174420114": [1, 2, 3, 4, 5],
    "entry.1040653638": [1, 2, 3, 4, 5],
    "entry.506373281":  [1, 2, 3, 4, 5],
    "entry.629996778":  [1, 2, 3, 4, 5],
    "entry.1249643401": [1, 2, 3, 4, 5],
}

# Realistic weights: skewed toward 4 and 5, including 3
WEIGHTS = [0, 0, 0.20, 0.40, 0.40]

def build_payload(session):
    # First, get the form to extract dynamic tokens
    get_url = FORM_URL.replace("formResponse", "viewform")
    r_get = session.get(get_url)
    
    import re
    fbzx_match = re.search(r'name="fbzx" value="(.*?)"', r_get.text)
    fbzx = fbzx_match.group(1) if fbzx_match else "-4835158315108403482"
    
    history_match = re.search(r'name="pageHistory" value="(.*?)"', r_get.text)
    page_history = history_match.group(1) if history_match else "0,1,2"
    
    payload = {}
    
    # Handle the required Basic Info fields
    payload["entry.2133561483"] = random.choice(["Male", "Female"])  # Gender (*)
    
    # Main rating fields
    for entry_id, options in FIELDS.items():
        value = random.choices(options, weights=WEIGHTS, k=1)[0]
        payload[entry_id] = str(value)
        # Add sentinel field for each entry (empty value)
        payload[entry_id + "_sentinel"] = ""
    
    # Add required Google Forms metadata fields
    import time as time_module
    current_time = int(time_module.time() * 1000)
    
    payload["dlut"] = current_time
    payload["hud"] = "true"
    payload["fvv"] = "1"
    payload["fbzx"] = fbzx
    payload["pageHistory"] = page_history
    
    return payload

def submit(session, count):
    success = 0
    fail = 0
    for i in range(1, count + 1):
        payload = build_payload(session)
        for attempt in range(1, 4):
            try:
                r = session.post(FORM_URL, data=payload, timeout=10)
                if r.status_code in (200, 302):
                    logging.info(f"[{i}/{count}] OK (attempt {attempt})")
                    success += 1
                    break
                else:
                    logging.warning(f"[{i}/{count}] HTTP {r.status_code} (attempt {attempt})")
            except requests.RequestException as e:
                logging.error(f"[{i}/{count}] Error: {e} (attempt {attempt})")
            time.sleep(2)
        else:
            fail += 1
        delay = random.uniform(2, 5)
        logging.info(f"  Waiting {delay:.1f}s...")
        time.sleep(delay)
    return success, fail

def main():
    parser = argparse.ArgumentParser(description="Google Form automation bot")
    parser.add_argument("--count", type=int, default=18, help="Number of submissions")
    args = parser.parse_args()

    logging.info(f"=== Starting {args.count} submissions at {datetime.now()} ===")
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})
    success, fail = submit(session, args.count)
    logging.info(f"=== Done: {success} succeeded, {fail} failed ===")

if __name__ == "__main__":
    main()
