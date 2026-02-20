# v2 Priority 1 Implementation — Deal Card Upgrades

**Status:** ✅ **COMPLETE**  
**Date:** 2026-02-20  
**Git commit:** `063c74c`  
**Branch:** `main`

## Summary

Implemented ONLY Priority 1 (sections 1a through 1d) from the v2 architecture spec. All 4 new metrics are now live in the SB1123 deal card pro forma section.

## Changes Made

### 1. Updated `calculateProForma()` function

**Added critical calculation:**
```javascript
const effective_buildable_sf = Math.min(l.lotSf * 1.25, maxUnits * 1750);
```

This is the foundation for all new metrics. SB1123 caps subdivisions at 10 lots, and Yardsworth's target product is 1,750 SF townhomes. Therefore:
- **Max sellable product = 17,500 SF** (10 units × 1,750 SF)
- Even if lot FAR allows more, you can only build 17,500 SF
- Excess lot SF is dead capital

**New return values:**
- `effective_buildable_sf` — the correct denominator for all per-SF calculations
- `land_basis_psf` — acquisition cost per buildable SF
- `target_buy_price` — price needed for 30% margin
- `headroom` — how far below/above target the asking price is
- `headroom_pct` — headroom as percentage of asking price
- `lot_efficiency` — percentage of FAR capacity actually used
- `return_on_cost` — profit as % of total cost (developer-friendly metric)

### 2. Updated deal card popup HTML

**1a. Land Basis per Product SF**
- Displays below "Buy / Unit" line
- Formula: `list_price / effective_buildable_sf`
- Color coding:
  - 🟢 Green: < $120/sf (great land basis)
  - 🟡 Yellow: $120-160/sf (workable)
  - 🔴 Red: > $160/sf (too expensive)

**1b. Target Buy Price (30% margin)**
- New 3-row section with green label
- Shows:
  - Target Buy (30% margin): The price at which this deal hits target margin
  - Asking Price: Current list price
  - Headroom: Dollar and percentage difference
- Headroom color coding:
  - 🟢 Green: Asking < Target (positive headroom = deal works at ask)
  - 🟡 Yellow: Asking 0-15% above Target (negotiable)
  - 🔴 Red: Asking >15% above Target (needs major price cut)
- **Uses Hood $/SF as exit assumption** — grounded in local comps

**1c. Lot Efficiency Score**
- Displays inline with Lot Size: "14,527 sf (97% efficient)"
- Formula: `effective_buildable_sf / (lot_sf * 1.25)`
- Color coding:
  - 🟢 Green: ≥ 85% efficient
  - 🟡 Yellow: 60-85% efficient
  - 🔴 Red: < 60% efficient
- Immediately flags oversized lots where you're buying dirt you can't use

**1d. Return on Cost**
- Added alongside existing "Margin on Revenue" (both displayed)
- Formula: `est_profit / total_cost`
- Developers think in return-on-cost
- Shows higher/clearer numbers than margin-on-revenue

### 3. Existing fields preserved

All existing deal card metrics remain unchanged:
- Buy / Unit
- Build / Unit
- Sell / Unit
- Total Cost
- Net Revenue
- Est Profit
- Profit / Unit
- Margin on Revenue

## Test Results

Created `test_v2_metrics.js` to validate calculations:

### Test Case 1: Sweet Spot Lot (14,527 SF)
```
Lot FAR capacity (1.25x): 18,158.75 SF
SB1123 product cap (10 × 1,750): 17,500 SF
Effective Buildable SF: 17,500 SF

✅ Land Basis per Product SF: $126/sf (YELLOW)
✅ Lot Efficiency: 96.4% (GREEN) — perfect utilization
✅ Target Buy Price: $4,042,500
   Asking Price: $2,200,000
   Headroom: +$1,842,500 (83.8%) (GREEN) — deal works!
```

### Test Case 2: Oversized Lot (31,730 SF)
```
Lot FAR capacity (1.25x): 39,662.5 SF
SB1123 product cap (10 × 1,750): 17,500 SF
Effective Buildable SF: 17,500 SF
⚠️  Wasted FAR: 22,162.5 SF

❌ Land Basis per Product SF: $257/sf (RED)
❌ Lot Efficiency: 44.1% (RED) — massive waste
   ⚠️ Paying for dirt you can't monetize!
```

### Test Case 3: Return on Cost vs Margin
```
Profit: $850,000
Total Cost: $3,200,000
Net Revenue: $4,050,000

✅ Return on Cost: 26.6%
   Margin on Revenue: 21.0%
   ✅ ROC shows clearer picture for developers
```

## Critical Implementation Details

1. **Used EXACT formula from spec:** `effective_buildable_sf = Math.min(lot_sf * 1.25, num_units * 1750)`
2. **All existing fields preserved:** These are ADDITIONS, not replacements
3. **Color coding matches spec exactly:** Green/Yellow/Red thresholds per section
4. **Target Buy uses Hood $/SF:** Grounded in local comp data, not global assumptions

## Visual Layout

The new deal card sections are organized as:

```
[Existing property info section]

─────────────────────────────────────
SB 1123 Pro Forma — 10 Townhomes • 1.25x FAR (17,500 sf) • Exit $830/sf

Buy / Unit                    Total Cost
Land Basis / Product SF       Effective Buildable SF

─────────────────────────────────────
Target Buy Price (30% Margin)

Target Buy                    Asking Price
Headroom

─────────────────────────────────────
Economics

Build / Unit                  Net Revenue
Sell / Unit                   Est Profit
Profit / Unit                 Return on Cost
Margin on Revenue

─────────────────────────────────────
ZIMAS Due Diligence
[existing checklist]
```

## What Was NOT Implemented

Per instructions, did NOT implement:
- Priority 2: Spread Heatmap
- Priority 3: Neighborhood Opportunity Scorer
- Priority 4: Off-Market Targets

These remain for future work.

## Verification

✅ All 4 new metrics display correctly  
✅ Color coding functions as specified  
✅ effective_buildable_sf formula used EXACTLY as spec'd  
✅ All existing deal card fields preserved  
✅ Test suite validates calculations  
✅ Committed with clear message  
✅ Pushed to GitHub (`mlucido/la-comps-map`)

## Next Steps

To see the changes live:
1. Navigate to `~/Dropbox (Personal)/la-comps-map/`
2. Open `index.html` in a browser
3. Click any SB1123-eligible listing (green circle markers)
4. Observe the 4 new metrics in the deal card popup

The tool now provides much clearer acquisition decision-making with:
- Land basis per product SF (shows if you're overpaying for dirt)
- Target buy price (shows exactly where this deal needs to be)
- Lot efficiency score (flags oversized lots with wasted FAR)
- Return on cost (clearer developer-friendly profit metric)
