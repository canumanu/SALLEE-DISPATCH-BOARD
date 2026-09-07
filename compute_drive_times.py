"""
compute_drive_times.py

Computes a drive-time matrix between all known locations (racetracks/training
centers, plus farms once addressed) using the Google Routes API, and writes
the result to drive_times.json for the dispatch board to read.

Same shape as sync_orders.py: run this on a schedule (GitHub Actions / cron),
publish the output JSON, and the dispatch board reads the static file with
zero live API calls at dispatch time.

Setup required (one-time, in Google Cloud Console):
  1. Create/select a project, enable billing (required even for free-tier usage).
  2. Enable the "Routes API".
  3. Create an API key, and restrict it to the Routes API only.
  4. Store the key as a GitHub Actions secret, e.g. GOOGLE_ROUTES_API_KEY.
     Never commit the key to the repo.

Usage:
  export GOOGLE_ROUTES_API_KEY="your-key-here"
  python compute_drive_times.py
"""

import json
import os
import sys
import time
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

API_KEY = os.environ.get("GOOGLE_ROUTES_API_KEY")
if not API_KEY:
    print("ERROR: set the GOOGLE_ROUTES_API_KEY environment variable first.")
    sys.exit(1)

ROUTES_API_URL = "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix"

# Google limits computeRouteMatrix to 625 elements per call (100 if using
# TRAFFIC_AWARE_OPTIMAL). We batch destinations to stay under that.
MAX_ELEMENTS_PER_CALL = 600

LOCATIONS_FILE = Path(__file__).parent / "locations.json"
OUTPUT_FILE = Path(__file__).parent / "drive_times.json"

# ---------------------------------------------------------------------------
# LOCATIONS
# ---------------------------------------------------------------------------
# locations.json should look like:
# [
#   {"code": "KEE", "name": "Keeneland", "address": "4201 Versailles Rd, Lexington, KY 40510"},
#   {"code": "BEL", "name": "Belmont Park", "address": "2150 Hempstead Turnpike, Elmont, NY 11003"},
#   ...
# ]
#
# Start this file with your real TRACK_ADDRESSES list from the Load Board
# (same 25ish tracks). Add farms/trainers to it over time as addresses
# become available for them.


def load_locations():
    if not LOCATIONS_FILE.exists():
        print(f"ERROR: {LOCATIONS_FILE} not found. Create it first (see comment in this script).")
        sys.exit(1)
    with open(LOCATIONS_FILE, "r", encoding="utf-8") as f:
        locations = json.load(f)
    if len(locations) < 2:
        print("ERROR: need at least 2 locations to compute a matrix.")
        sys.exit(1)
    return locations


# ---------------------------------------------------------------------------
# GOOGLE ROUTES API CALL
# ---------------------------------------------------------------------------

def build_waypoint(location):
    return {"waypoint": {"address": location["address"]}}


def call_route_matrix(origins, destinations):
    """
    Calls computeRouteMatrix for one batch of origins x destinations.
    Returns the parsed JSON list of matrix elements.
    """
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": API_KEY,
        # status is required in the field mask, or failures look like successes
        "X-Goog-FieldMask": "originIndex,destinationIndex,status,condition,distanceMeters,duration",
    }
    body = {
        "origins": [build_waypoint(o) for o in origins],
        "destinations": [build_waypoint(d) for d in destinations],
        "travelMode": "DRIVE",
        "routingPreference": "TRAFFIC_UNAWARE",  # typical drive time, not live traffic
    }
    resp = requests.post(ROUTES_API_URL, headers=headers, json=body, timeout=30)
    resp.raise_for_status()
    return resp.json()


def parse_duration_seconds(duration_str):
    """Google returns durations like '1234s' - strip the trailing 's'."""
    if not duration_str:
        return None
    return int(str(duration_str).rstrip("s"))


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    locations = load_locations()
    n = len(locations)
    print(f"Loaded {n} locations. Computing a {n}x{n} drive-time matrix...")

    # Batch destinations to stay under the element limit.
    # elements per call = len(origins_batch) * len(destinations_batch)
    dest_batch_size = max(1, MAX_ELEMENTS_PER_CALL // n)

    matrix = {}  # matrix[origin_code][destination_code] = {minutes, miles}
    for loc in locations:
        matrix[loc["code"]] = {}

    for start in range(0, n, dest_batch_size):
        dest_batch = locations[start:start + dest_batch_size]
        print(f"  Calling API for destinations {start}-{start+len(dest_batch)-1}...")
        try:
            elements = call_route_matrix(locations, dest_batch)
        except requests.exceptions.RequestException as e:
            print(f"  ERROR calling Routes API: {e}")
            sys.exit(1)

        for el in elements:
            status = el.get("status", {})
            if status and status.get("code"):
                # Non-zero status code means this pair failed (e.g. no route found)
                continue
            origin_loc = locations[el["originIndex"]]
            dest_loc = dest_batch[el["destinationIndex"]]
            duration_s = parse_duration_seconds(el.get("duration"))
            distance_m = el.get("distanceMeters")
            if duration_s is None:
                continue
            matrix[origin_loc["code"]][dest_loc["code"]] = {
                "minutes": round(duration_s / 60),
                "miles": round(distance_m / 1609.34, 1) if distance_m else None,
            }

        time.sleep(0.5)  # gentle pacing between batches

    output = {
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "locations": [{"code": l["code"], "name": l["name"]} for l in locations],
        "matrix": matrix,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"Wrote {OUTPUT_FILE} ({n*n} pairs, {n} locations).")


if __name__ == "__main__":
    main()
