import requests
import random
import time
import argparse
import logging
import re
from collections import Counter
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

GENDER_ENTRY = "entry.2133561483"
GENDERS = ["Male", "Female"]
SCALE = [1, 2, 3, 4, 5]

# Sections in form order. Single source of truth for both the payload and the report.
SECTIONS = [
    ("Sales & Financial Issues", [
        "entry.1073028820", "entry.1534527371", "entry.1824670283",
        "entry.2065257654", "entry.1958451722",
    ]),
    ("Operational Performance", [
        "entry.1158536296", "entry.1208633648", "entry.125228566",
        "entry.229164637", "entry.931029854",
    ]),
    ("Marketing Performance", [
        "entry.838163659", "entry.1981633268", "entry.1025240302",
        "entry.2132415631", "entry.1395475420",
    ]),
    ("Human Resource Performance", [
        "entry.1896395260", "entry.1604475851", "entry.501751395",
        "entry.1259896805", "entry.1911932776",
    ]),
    ("SWOT Assessment", [
        "entry.2048562672", "entry.637855574", "entry.435189453",
        "entry.2073197847", "entry.753148199",
    ]),
    ("Functional Suitability", [
        "entry.1770471280", "entry.1306628739", "entry.1863604018",
        "entry.1053336508", "entry.620134986",
    ]),
    ("Performance Efficiency", [
        "entry.1670338690", "entry.1457259386", "entry.461795711",
        "entry.486281422", "entry.1193061868",
    ]),
    ("Compatibility", [
        "entry.509544094", "entry.1867347108", "entry.964321943",
        "entry.610803395", "entry.857113999",
    ]),
    ("Usability", [
        "entry.1084420106", "entry.989625805", "entry.1933737404",
        "entry.1901357432", "entry.723747481",
    ]),
    ("Security", [
        "entry.1174420114", "entry.1040653638", "entry.506373281",
        "entry.629996778", "entry.1249643401",
    ]),
]

FIELDS = {eid: SCALE for _, ids in SECTIONS for eid in ids}

# Realistic weights: skewed toward 4 and 5, including 3
WEIGHTS = [0, 0, 0.20, 0.40, 0.40]

MALE_NAMES = [
    "Liam", "Noah", "Ethan", "Lucas", "Mason", "James",
    "Aiden", "Daniel", "Ryan", "Owen", " Caleb", "Nathan",
]
FEMALE_NAMES = [
    "Emma", "Olivia", "Sophia", "Ava", "Isabella", "Mia",
    "Charlotte", "Amelia", "Harper", "Evelyn", "Abigail", "Ella",
]
LAST_NAMES = [
    "Novak", "Horvat", "Petrov", "Markovic", "Jovanovic", "Kovac",
    "Simic", "Djordjevic", "Nikolic", "Ilic", "Stankovic", "Radic",
    "Vukovic", "Babic", "Mladenovic", "Lukic",
]


def make_name(rng):
    """A synthetic respondent name used as a local tracking label."""
    if rng.random() < 0.5:
        return rng.choice(MALE_NAMES), "Male"
    return rng.choice(FEMALE_NAMES), "Female"


def build_payload(session=None, rng=None, name=None, gender=None):
    """Build a form payload. With session=None nothing is fetched over the network."""
    rng = rng or random
    if session is None:
        fbzx = "DRYRUN"
        page_history = "0,1,2"
    else:
        get_url = FORM_URL.replace("formResponse", "viewform")
        r_get = session.get(get_url)
        fbzx_match = re.search(r'name="fbzx" value="(.*?)"', r_get.text)
        fbzx = fbzx_match.group(1) if fbzx_match else "-4835158315108403482"
        history_match = re.search(r'name="pageHistory" value="(.*?)"', r_get.text)
        page_history = history_match.group(1) if history_match else "0,1,2"

    payload = {}
    payload[GENDER_ENTRY] = gender or rng.choice(GENDERS)

    for entry_id, options in FIELDS.items():
        value = rng.choices(options, weights=WEIGHTS, k=1)[0]
        payload[entry_id] = str(value)
        payload[entry_id + "_sentinel"] = ""

    current_time = int(time.time() * 1000)
    payload["dlut"] = current_time
    payload["hud"] = "true"
    payload["fvv"] = "1"
    payload["fbzx"] = fbzx
    payload["pageHistory"] = page_history

    return payload, name


def log_payload(index, total, name, payload):
    """Live log: one header line per submission, one line per section."""
    logging.info("[%d/%d] respondent: %s  (gender: %s)",
                 index, total, name, payload[GENDER_ENTRY])
    for section, ids in SECTIONS:
        values = " ".join(payload[eid] for eid in ids)
        logging.info("      %-30s : %s", section, values)
    logging.info("      %-30s : dlut=%s hud=%s fvv=%s fbzx=%s pageHistory=%s",
                 "metadata", payload["dlut"], payload["hud"], payload["fvv"],
                 payload["fbzx"], payload["pageHistory"])


def fmt_counts(counter, keys):
    total = sum(counter.values()) or 1
    return "  ".join(
        "%s:%d (%.1f%%)" % (k, counter.get(k, 0), counter.get(k, 0) / total * 100)
        for k in keys
    )


def log_summary(stats, genders, names, count, dry_run):
    total_answers = sum(sum(c.values()) for c in stats.values())
    logging.info("")
    logging.info("=== SUMMARY%s ===", " (dry run, nothing submitted)" if dry_run else "")
    logging.info("Submissions generated : %d", count)
    logging.info("Unique names          : %d", len(set(names)))
    logging.info("Gender                : %s", fmt_counts(genders, GENDERS))
    logging.info("")
    logging.info("Per-field counts across %d submissions:", count)
    for section, ids in SECTIONS:
        logging.info("  %s", section)
        for eid in ids:
            logging.info("    %-22s %s", eid, fmt_counts(stats[eid], SCALE))
    logging.info("")
    logging.info("OVERALL (%d scale answers across %d fields):",
                 total_answers, len(FIELDS))
    overall = Counter()
    for c in stats.values():
        overall.update(c)
    logging.info("  %s", fmt_counts(overall, SCALE))
    logging.info("")


def submit(session, count, rng, dry_run):
    stats = {eid: Counter() for eid in FIELDS}
    genders = Counter()
    names = []
    success = 0
    fail = 0

    for i in range(1, count + 1):
        name, gender = make_name(rng)
        payload, _ = build_payload(
            session=None if dry_run else session, rng=rng,
            name=name, gender=gender,
        )
        names.append(name)
        genders[gender] += 1
        for eid in FIELDS:
            stats[eid][int(payload[eid])] += 1

        log_payload(i, count, name, payload)

        if not dry_run:
            for attempt in range(1, 4):
                try:
                    r = session.post(FORM_URL, data=payload, timeout=10)
                    if r.status_code in (200, 302):
                        logging.info("      -> OK (attempt %d)", attempt)
                        success += 1
                        break
                    else:
                        logging.warning("      -> HTTP %s (attempt %d)", r.status_code, attempt)
                except requests.RequestException as e:
                    logging.error("      -> Error: %s (attempt %d)", e, attempt)
                time.sleep(2)
            else:
                fail += 1
            delay = rng.uniform(2, 5)
            logging.info("      waiting %.1fs...", delay)
            time.sleep(delay)

    log_summary(stats, genders, names, count, dry_run)
    return success, fail


def main():
    parser = argparse.ArgumentParser(
        description="Google Form automation bot",
        epilog="Respondent names are local tracking labels only; they are not "
               "submitted to the form.",
    )
    parser.add_argument("--count", type=int, default=18, help="Number of submissions")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Generate and log payloads without sending anything",
    )
    parser.add_argument(
        "--seed", type=int, default=None,
        help="Seed the RNG for reproducible output",
    )
    args = parser.parse_args()

    mode = "dry run" if args.dry_run else "live"
    logging.info("=== Starting %d submissions (%s) at %s ===",
                 args.count, mode, datetime.now())
    if args.seed is not None:
        logging.info("Using seed %d", args.seed)

    rng = random.Random(args.seed)
    session = None if args.dry_run else requests.Session()
    if session is not None:
        session.headers.update({"User-Agent": "Mozilla/5.0"})

    success, fail = submit(session, args.count, rng, args.dry_run)
    if args.dry_run:
        logging.info("=== Done: %d payloads generated, 0 sent ===", args.count)
    else:
        logging.info("=== Done: %d succeeded, %d failed ===", success, fail)


if __name__ == "__main__":
    main()
