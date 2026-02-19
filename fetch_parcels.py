#!/usr/bin/env python3
"""
fetch_parcels.py
Fetches parcel lot area + fire zone status from LA County ArcGIS for each listing.

For each listing, queries two ArcGIS services:
  1. Parcel service — lot area (Shape.STArea() in sq ft), AIN, assessed values
  2. Hazards service — VHFHSZ fire zone status

Reads:  redfin_merged.csv (directly, to avoid chicken-and-egg with listings.js)
Writes: parcels.json — keyed by "lat,lng"

Supports incremental runs (skips already-computed listings).

Usage:
  python3 fetch_parcels.py          # All listings (~1-3 min)
  python3 fetch_parcels.py --test   # First 10 only
"""

import csv, json, os, sys, time, re
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# ── Config ──
PARCEL_URL = "https://public.gis.lacounty.gov/public/rest/services/LACounty_Cache/LACounty_Parcel/MapServer/0/query"
FIRE_URL = "https://public.gis.lacounty.gov/public/rest/services/LACounty_Dynamic/Hazards/MapServer/2/query"
MAX_WORKERS = 25
OUTPUT_FILE = "parcels.json"
ENVELOPE_OFFSET = 0.00002  # ~2m envelope around point for parcel query

# LA County bounding box (same as listings_build.py)
LA_LAT_MIN, LA_LAT_MAX = 33.70, 34.85
LA_LNG_MIN, LA_LNG_MAX = -118.95, -117.55


def query_parcel(lat, lng, retries=2):
    """Query LA County parcel service with small envelope to get containing parcel."""
    env = {
        "xmin": lng - ENVELOPE_OFFSET,
        "ymin": lat - ENVELOPE_OFFSET,
        "xmax": lng + ENVELOPE_OFFSET,
        "ymax": lat + ENVELOPE_OFFSET,
        "spatialReference": {"wkid": 4326}
    }
    params = {
        "geometry": json.dumps(env),
        "geometryType": "esriGeometryEnvelope",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "AIN,Roll_LandValue,Roll_ImpValue,SitusAddress,Shape.STArea()",
        "returnGeometry": "false",
        "f": "json",
    }
    for attempt in range(retries + 1):
        try:
            resp = requests.get(PARCEL_URL, params=params, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                features = data.get("features", [])
                if features:
                    attrs = features[0].get("attributes", {})
                    area = attrs.get("Shape.STArea()")
                    return {
                        "lotSf": round(area) if area else None,
                        "ain": attrs.get("AIN", ""),
                        "landValue": attrs.get("Roll_LandValue"),
                        "impValue": attrs.get("Roll_ImpValue"),
                        "situsAddress": attrs.get("SitusAddress", ""),
                    }
                return None  # No parcel found at this location
            elif resp.status_code in (429, 503):
                time.sleep(3 + attempt * 3)
                continue
        except Exception:
            if attempt < retries:
                time.sleep(2)
    return None


def query_fire_zone(lat, lng, retries=2):
    """Query LA County Hazards service for VHFHSZ fire zone status."""
    params = {
        "geometry": f"{lng},{lat}",
        "geometryType": "esriGeometryPoint",
        "inSR": 4326,
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "HAZ_CLASS",
        "returnGeometry": "false",
        "f": "json",
    }
    for attempt in range(retries + 1):
        try:
            resp = requests.get(FIRE_URL, params=params, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                features = data.get("features", [])
                if features:
                    haz = features[0].get("attributes", {}).get("HAZ_CLASS", "")
                    return haz == "Very High"
                return False  # No fire zone feature at this point
            elif resp.status_code in (429, 503):
                time.sleep(3 + attempt * 3)
                continue
        except Exception:
            if attempt < retries:
                time.sleep(2)
    return None  # Query failed


def fetch_parcel_data(lat, lng):
    """Fetch both parcel info and fire zone status for a single listing."""
    parcel = query_parcel(lat, lng)
    fire = query_fire_zone(lat, lng)

    if parcel is None and fire is None:
        return None

    result = {}
    if parcel:
        result["lotSf"] = parcel["lotSf"]
        result["ain"] = parcel["ain"]
        result["landValue"] = parcel["landValue"]
        result["impValue"] = parcel["impValue"]
        if parcel.get("situsAddress"):
            result["situsAddress"] = parcel["situsAddress"]
    if fire is not None:
        result["fireZone"] = fire

    return result if result else None


def load_listings_from_csv():
    """Load listing lat/lng from redfin_merged.csv (same logic as listings_build.py)."""
    csv_file = "redfin_merged.csv"
    if not os.path.exists(csv_file):
        print(f"  No {csv_file} found.")
        sys.exit(1)

    listings = []
    with open(csv_file, encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                lat = float(row.get("LATITUDE") or 0)
                lng = float(row.get("LONGITUDE") or 0)
                if not (LA_LAT_MIN <= lat <= LA_LAT_MAX and LA_LNG_MIN <= lng <= LA_LNG_MAX):
                    continue
                status = row.get("STATUS", "").strip()
                if status != "Active":
                    continue
                price = float(re.sub(r"[^0-9.]", "", row.get("PRICE") or "0") or 0)
                if price <= 0:
                    continue
                listings.append((round(lat, 6), round(lng, 6)))
            except Exception:
                continue
    return listings


def main():
    test_mode = "--test" in sys.argv

    listings = load_listings_from_csv()

    # Load existing (incremental — skip already computed)
    existing = {}
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE) as f:
            existing = json.load(f)
        print(f"  Loaded {len(existing):,} cached parcels")

    # Build work list
    work = []
    for lat, lng in listings:
        key = f"{lat},{lng}"
        if key not in existing:
            work.append((lat, lng, key))

    if test_mode:
        work = work[:10]

    total = len(work)
    print(f"\n{'='*60}")
    print(f"  LA County ArcGIS — Parcel + Fire Zone Fetcher")
    if test_mode:
        print(f"  ** TEST MODE — 10 listings **")
    print(f"{'='*60}")
    print(f"\n  Listings from CSV: {len(listings):,}")
    print(f"  Already cached: {len(existing):,}")
    print(f"  To process: {total:,}")
    print(f"  Workers: {MAX_WORKERS}")
    est_min = total * 2 / MAX_WORKERS * 0.5 / 60
    print(f"  Est. time: {est_min:.1f} minutes\n")

    if total == 0:
        print("  All listings already have parcel data. Done!\n")
        return

    results = dict(existing)
    completed = 0
    errors = 0
    start = time.time()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {}
        for lat, lng, key in work:
            fut = pool.submit(fetch_parcel_data, lat, lng)
            futures[fut] = key

        for fut in as_completed(futures):
            key = futures[fut]
            completed += 1
            try:
                data = fut.result()
                if data is not None:
                    results[key] = data
                else:
                    errors += 1
            except Exception:
                errors += 1

            if completed % 50 == 0 or completed == total:
                elapsed = time.time() - start
                rate = completed / elapsed if elapsed > 0 else 0
                eta = (total - completed) / rate / 60 if rate > 0 else 0
                sys.stdout.write(
                    f"\r  [{completed:>5,}/{total:,}] "
                    f"{rate:.1f}/s | "
                    f"{errors} err | "
                    f"ETA {eta:.1f}m   "
                )
                sys.stdout.flush()

                # Checkpoint every 500
                if completed % 500 == 0:
                    with open(OUTPUT_FILE, "w") as f:
                        json.dump(results, f)

    elapsed = time.time() - start

    # Final save
    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f)

    print(f"\n\n  Done in {elapsed / 60:.1f} minutes")
    print(f"  Total parcels: {len(results):,}")
    print(f"  Errors: {errors}")

    # Stats
    with_lot = sum(1 for v in results.values() if v.get("lotSf"))
    with_fire = sum(1 for v in results.values() if v.get("fireZone"))
    lots = [v["lotSf"] for v in results.values() if v.get("lotSf")]
    print(f"\n  With lot size: {with_lot:,}/{len(results):,}")
    print(f"  In VHFHSZ: {with_fire:,}")
    if lots:
        lots.sort()
        print(f"  Lot SF: median {lots[len(lots)//2]:,}, min {lots[0]:,}, max {lots[-1]:,}")

    print(f"\n  Written: {OUTPUT_FILE}")
    print(f"  Next: python3 listings_build.py\n")


if __name__ == "__main__":
    try:
        import requests
    except ImportError:
        print("\n  'requests' not found. Install: pip3 install requests\n")
        sys.exit(1)
    main()
