#!/bin/bash
# refresh.sh — One-click data refresh for SB 1123 Deal Finder
# Pulls fresh Redfin listings, rebuilds all enrichment, and pushes to GitHub Pages.
#
# Usage:
#   ./refresh.sh           # Full refresh (listings + comps)
#   ./refresh.sh --quick   # Listings only (skip sold comps)

set -e
cd "$(dirname "$0")"

echo ""
echo "============================================================"
echo "  SB 1123 Deal Finder — Data Refresh"
echo "============================================================"
echo ""

QUICK=false
if [ "$1" = "--quick" ]; then
  QUICK=true
  echo "  Mode: Quick (listings only, skip sold comps)"
else
  echo "  Mode: Full (listings + sold comps)"
fi
echo ""

# Step 1: Fetch fresh active listings from Redfin
echo "📥 Step 1: Fetching active listings from Redfin..."
python3 fetch_listings.py
echo ""

# Step 2: Optionally refresh sold comps
if [ "$QUICK" = false ]; then
  echo "📥 Step 2: Fetching sold comps from Redfin..."
  python3 fetch_sold_comps.py
  echo ""

  echo "🔨 Step 3: Building data.js (sold comps)..."
  python3 build_comps.py
  echo ""
fi

# Step 3: Rebuild listings.js with all enrichment
echo "🔨 Building listings.js (zone $/SF, new-con, slope, city)..."
python3 listings_build.py
echo ""

# Step 4: Push to GitHub Pages
echo "🚀 Pushing to GitHub Pages..."
git add data.js listings.js slopes.json
git commit -m "Refresh listing data $(date +%Y-%m-%d)" --allow-empty
git push
echo ""

echo "============================================================"
echo "  ✅ Done! Site will update in ~60s:"
echo "  https://mlucido.github.io/la-comps-map/"
echo "============================================================"
echo ""
