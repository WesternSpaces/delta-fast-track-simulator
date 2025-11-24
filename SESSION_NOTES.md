# Session Notes - November 23, 2025

## Summary
Major refinements to the Delta Fast Track Simulator focusing on accuracy, simplification, and appropriate messaging for a conservative community.

---

## Critical Fixes

### 1. City Investment Calculation (MOST IMPORTANT)
**Issue:** City investment was showing ~$1,030,000 - way too high for a conservative community
**Root Cause:** Included density bonus value (~$660K) and time savings ($50K) which aren't actual city costs
**Fix:** Changed calculation to show ONLY fee waivers (~$320K)

```python
# Before:
city_investment = self.dev['total_benefits']  # Included everything

# After:
city_investment = self.dev['total_fee_waivers']  # Only actual dollars spent
```

**Impact:** City investment now shows only real taxpayer dollars (fee waivers), not theoretical values. This is critical for fiscal credibility.

---

## Fee Calculation Improvements

### Verified All Fees Against 2025 Fee Schedule
- **Planning Fees:** $500 + ($20 × units) + $250 final plat
- **Building Permits:** Tiered formula from Table 3B
- **Tap & Sewer Fees:**
  - Water BSIF: $86,100 + $1,500/unit
  - Water Tapping: $12,420 (was missing!)
  - Sewer BSIF: $154,000 + $2,600/unit
- **Use Tax:** 3% of materials (60% of construction cost)

### Added Fee Transparency
- All fee calculations now documented in consolidated Methodology expander
- Removed individual "ℹ️" expanders (too cluttered)
- One comprehensive section with all technical details

---

## Interface Streamlining

### Merged Tabs: 4 → 3
**Before:**
- Tab 1: Developer Economics
- Tab 2: Community Benefit
- Tab 3: Comparisons
- Tab 4: Export & Share

**After:**
- Tab 1: **Results** (Developer Economics + Community Benefit combined)
- Tab 2: **Comparisons**
- Tab 3: **Export**

**Benefits:**
- All key results visible without switching tabs
- Developer economics and community impact side-by-side
- Less cluttered, more focused

### Removed Redundant Content
- Model Assumptions info box (duplicated Methodology)
- "How the Numbers Work" expander in Community Benefit tab
- Ownership period explanation in Comparisons tab
- ~100+ lines of duplicate text removed

### Consolidated Methodology
- Created single "📖 Methodology & Data Sources" expander
- Appears once at top, before tabs
- Contains:
  - Model assumptions
  - Calculation methodology
  - All fee formulas with examples
  - Data sources
  - Capital stack context

---

## Policy Slider Adjustments

### Increased Granularity
- **Density Bonus:** Max increased from 30% → 50%
- **Bonus Affordable %:** Step from 10% → 5% (enables 25% option)
- **Tap Fee Reduction:** Changed from select_slider to regular slider, 5% increments
- **Use Tax Rebate:** Max 50% → 100%, step 10% → 5%

### Added AMI Threshold Controls
- Moved to "Advanced Project Parameters" expander
- Rental AMI: 30-80% (step 10%)
- Ownership AMI: 80-120% (step 10%)
- Available if focus group wants to discuss lowering 80% threshold
- Changed from sliders to number_input for UI consistency

---

## Terminology Updates

### "Feasible" → "Fast Track Adds Value"
**Why:** "Feasible" implied full project feasibility, but analysis only shows Fast Track incentive value vs. affordability costs. Actual projects need full capital stack (LIHTC, grants, etc.)

**Updated:**
- Main metric card: "✓ Fast Track Adds Value" / "✗ Cost Exceeds Benefits"
- Comparison scatter plot legend

### "Local Workers Housed" → "Subsidized Workers Housed"
**Why:** Workers could live in any units (market or affordable). "Subsidized" clarifies these are workers in income-restricted units specifically.

**Updated in:**
- Workforce Housing Impact table
- Caption text
- Methodology data sources

---

## Visual Improvements

### Rental Income Premium Box
- Moved from cramped right column to full width
- Positioned at top of Developer Economics (right after heading)
- Green success box highlights key insight about 80% AMI premium
- More prominent placement for important discussion point

### Cleaned Up Tables
- Removed "Unit Breakdown" row from City Investment (no longer needed since projects are rental OR ownership)
- Removed blank line before "TOTAL DEVELOPER COSTS"

---

## Documentation Added

### Workforce Metrics in Methodology
Added to Data Sources section:
- Subsidized workers housed: 1.5 workers per affordable household
- Population served: 2.3 persons per household (Delta County average)
- Construction jobs: 0.5 jobs per unit (temporary)

### Capital Stack Context
Added prominent note explaining Fast Track is just one piece of financing:
- LIHTC (Low Income Housing Tax Credits)
- Grant funding (HOME, CDBG, state funds)
- Land contribution/discount
- Partnership equity
- Debt financing
- Developer equity

---

## Git Commits Made (17 total)

1. Fee calculation transparency with expandable info icons
2. Tap/sewer fees and use tax calculations with accurate 2025 data
3. Add 25% option to bonus affordability requirement slider
4. Change tap fee reduction to slider with 5% increments
5. Add AMI threshold sliders back to sidebar
6. Fix currency formatting (LaTeX rendering issues)
7. Move AMI thresholds to Advanced Parameters
8. Fix sidebar expander text visibility
9. Change AMI controls to number inputs
10. Fix input field text color in sidebar
11. Increase use tax rebate to 100% maximum
12. Consolidate methodology into single comprehensive expander
13. Streamline interface: merge tabs, remove redundant content
14. Remove unit breakdown from City Investment table
15. Add workforce metrics to methodology
16. Move rental premium box to top, full width
17. Remove blank line in costs table
18. **Fix city investment calculation (CRITICAL)**
19. Change to "Subsidized Workers Housed"

---

## Current State

### Live URL
**Streamlit Cloud:** https://delta-fast-track-simulator-qrzf2t87mqwzfgwporenqz.streamlit.app

### GitHub Repository
**Repo:** https://github.com/WesternSpaces/delta-fast-track-simulator

### Auto-Deployment
- Any push to `main` branch auto-deploys to Streamlit Cloud (~2 min)
- No manual deployment needed

---

## Key Numbers (Default 20-unit scenario)

**Developer Economics:**
- Total Benefits: ~$1,030,000
  - Density Bonus: ~$660,000
  - Fee Waivers: ~$320,000
  - Time Savings: $50,000
- Total Costs: ~$311,000 (rental units, 30 years at 80% AMI)
- Net Developer Gain: ~$719,000 ✓ Fast Track Adds Value

**City Investment:**
- Total Investment: ~$320,000 (fee waivers only)
- Cost per Unit-Year: ~$1,524
- 20-Year Cost: ~$320,000 (for 30-year term)
- Affordable Units: 7 units

**Community Impact:**
- Total Units: 24 (20 base + 4 bonus)
- Subsidized Workers: ~10 workers
- Construction Jobs: ~12 jobs

---

## Important Notes for Next Session

### Conservative Community Considerations
1. **Show only actual dollars spent** - No theoretical values
2. **Fee waivers are real costs** - Tax revenue foregone
3. **Density bonus is NOT a cost** - Just allowing more units
4. **Be precise with terminology** - "Subsidized" not "local workers"
5. **Capital stack context matters** - Fast Track alone won't make projects happen

### Focus Group Discussion Points
1. **80% AMI threshold** - Sarah hopes they'll discuss lowering it (too high)
2. **Affordability period** - Compare 5, 15, 20, 30, 50-year options
3. **Rental income premium** - At 80% AMI, CHFA rents exceed market rents
4. **Cost efficiency** - Cost per unit-year comparison across different periods

### Known Assumptions
- Unit mix: 20% 1BR, 60% 2BR, 20% 3BR
- Construction cost: $75,000/unit
- Land value: $90,000/unit
- Market rent 2BR: $1,425/mo (confirmed from Grand Mesa Flats)
- Fast Track time savings: $50,000

---

## Files Structure

```
meeting-one/
├── fast_track_simulator.py      # Main application (~1,700 lines)
├── requirements.txt              # Python dependencies
├── README.md                     # Full documentation
├── DEPLOY_TO_STREAMLIT.md       # Deployment guide
├── QUICKSTART.md                # Quick start
├── SIMULATOR_OVERVIEW.md        # Project overview
├── SESSION_NOTES.md             # This file
├── .gitignore                   # Git config
│
├── Data/                        # Source data
│   ├── 2025_fee_schedule(4).pdf
│   └── density-bonus-calculations+jlo.xlsx
│
└── Visuals/                     # Charts
    └── delta_ami_policy_tradeoffs.svg
```

---

## To Resume Work

1. **Open simulator locally:**
   ```bash
   cd "/Users/sarah/Documents/Western Spaces/Claude/delta/meeting-one"
   streamlit run fast_track_simulator.py
   ```

2. **Check live version:**
   https://delta-fast-track-simulator-qrzf2t87mqwzfgwporenqz.streamlit.app

3. **Review git history:**
   ```bash
   git log --oneline
   ```

4. **Common edits:**
   - Fee calculations: Lines 180-250 (FeeCalculator class)
   - City investment: Line 440 (CommunityBenefitAnalysis)
   - Policy sliders: Lines 700-850 (main sidebar)
   - Display tables: Lines 1050-1400 (Results tab)

---

## Questions to Consider

- Should we add scenario saving/loading?
- Do we need comparison mode (side-by-side scenarios)?
- Should we add Monte Carlo sensitivity analysis?
- Do we want to track which scenarios were viewed most?
- Should we add a "recommended scenario" based on cost efficiency?

---

## Contact

**For Technical Issues:** sarah@westernspaces.com
**Focus Group:** Dynamic Planning + Science facilitators
**Meeting Date:** TBD

---

*Session ended: November 23, 2025, ~11:00 PM*
