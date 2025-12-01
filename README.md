# Delta Fast Track Incentive Tradeoff Simulator

Interactive web application for exploring policy decisions on the City of Delta Fast Track Program for affordable housing development under Proposition 123.

## Overview

This simulator helps the Focus Group visualize tradeoffs between:
- **Affordability period** (5-99 years)
- **AMI thresholds** (60%, 80%, 100%, 110%, 120%)
- **Density bonuses** (0-50%)
- **Fee waivers and reductions** (building permits, tap fees, use tax)

It calculates real-time impacts on:
- Developer feasibility and ROI
- City costs and investment
- Affordable units created
- Long-term community benefit

## Quick Start

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run fast_track_simulator.py
```

The app will open in your browser at `http://localhost:8501`

### Deployment to Streamlit Cloud

1. **Push to GitHub:**
   ```bash
   git init
   git add .
   git commit -m "Initial commit: Delta Fast Track Simulator"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/delta-fast-track-simulator.git
   git push -u origin main
   ```

2. **Deploy on Streamlit Cloud:**
   - Go to https://streamlit.io/cloud
   - Sign in with GitHub
   - Click "New app"
   - Select your repository, branch (`main`), and file (`fast_track_simulator.py`)
   - Click "Deploy"

Your app will be live at: `https://YOUR_APP_NAME.streamlit.app`

**Live App:** https://delta-fast-track-simulator-qrzf2t87mqwzfgwporenqz.streamlit.app/

## Features

### Policy Controls
- **Affordability Requirements:** Period, AMI thresholds, minimum percentages
- **Density Bonus:** Percentage and requirements
- **Fee Waivers:** Planning, building permits, tap/system fees, use tax rebates
- **Project Parameters:** Customize unit count, costs, market rents

### Analysis Views

**Instructions Tab:**
- Current draft settings and baseline assumptions
- What policy questions to explore
- Step-by-step guide to finding your "sweet spot"
- Downloadable printable instructions

**Results Tab:**
- Benefits vs costs bar chart
- Developer Net Gain indicator (green/red)
- City investment efficiency metrics
- Detailed breakdowns (expandable)

**Comparisons Tab:**
- Tradeoff scatter plot (affordability period vs city cost)
- Side-by-side tables by affordability period
- AMI threshold comparisons (rental and ownership)

**Export Tab:**
- Download results as CSV
- Summary tables
- Policy settings snapshot

## Data Sources

- **2025 Delta County AMI data:** HUD Income Limits via CHFA
- **City of Delta 2025 Fee Schedule:** Official city document
- **Construction costs:** Grand Junction $120-180/sq ft (HomeBlue); Black Canyon Flats Montrose $22M/60 units
- **Land costs:** Delta County avg $6,795/acre undeveloped (LandSearch)
- **Market rents:** Grand Mesa Flats, Delta CO (Nov 2025)
- **Incentive Policy Assessment:** RPI Consulting, February 2025

## Technical Details

### Core Calculations

**Developer Pro Forma:**
```
Total Benefits = Density Bonus Value + Fee Waivers + Time Savings
Total Costs = Lost Rent × Affordable Units × Years
Net Position = Total Benefits - Total Costs
```

**Community Analysis:**
```
Cost per Unit-Year = City Investment / (Units × Years)
20-Year Cost = City Investment × (20 / Affordability Period)
```

**Fee Calculations:**
- Building permits: Tiered formula from Table 3B
- Tap/system fees: Water + Sewer based on unit count
- Use tax: 3% of materials cost with optional rebate

### Default Values (20-Unit Example)

- **Base units:** 20
- **Density bonus:** 20% (4 bonus units)
- **Total units:** 24
- **Affordable requirement:** 25% of base + 50% of bonus = 7 units
- **Market rent:** $1,425/month (Grand Mesa Flats, Nov 2025)
- **Affordability period:** 15 years (current draft)
- **Construction cost:** $200,000/unit (based on non-Denver CO avg)
- **Land/dev value:** $35,000/unit (Delta County avg)

## For Focus Group Members

### Key Questions to Explore

1. **What affordability period balances developer feasibility with community benefit?**
   - Compare 5, 15, 20, and 30-year options
   - Look at cost per unit-year and 20-year totals

2. **How do AMI thresholds affect the rent gap and developer costs?**
   - 60% AMI: Deeper affordability, higher developer cost
   - 80% AMI: Moderate affordability, lower developer cost

3. **Is the density bonus sufficient to offset affordable unit costs?**
   - Adjust density bonus percentage
   - Change the % of bonus units that must be affordable

4. **How should fee reductions tier with affordability period?**
   - Current proposal: 30%/60%/100% by term length
   - Test different combinations

5. **What scenarios make projects "pencil out" for developers?**
   - Developer Net Gain must be positive
   - Look for ROI > 5-10%

## Customization

### Adjusting Fees

Edit the `FeeCalculator` class in `fast_track_simulator.py` to update:
- Building permit fee tiers
- Tap and system improvement fees
- Use tax percentages

### Adding New Scenarios

Create preset scenarios in the sidebar:
```python
if st.sidebar.button("Load: Neighboring Community Comparison"):
    st.session_state.affordability_period = 30
    st.session_state.rental_ami = 0.60
    # ... set other values
```

### Modifying Calculations

Update the `DeveloperProForma` or `CommunityBenefitAnalysis` classes to:
- Add new cost/benefit categories
- Change valuation assumptions
- Include additional metrics

## Support

For questions or issues:
- **Technical support:** Review the Streamlit documentation at https://docs.streamlit.io
- **Policy questions:** Contact the City of Delta Focus Group facilitators
- **Data updates:** Check with Dynamic Planning + Science & Western Spaces

## Version History

- **v1.1 (December 2025):** Focus Group Meeting #2 Updates
  - Added Instructions tab with guided walkthrough
  - Updated construction costs with local Western Slope data
  - Default affordability period changed to 15 years
  - Added printable instructions download

- **v1.0 (November 2025):** Initial release for Focus Group Meeting
  - Core pro forma calculations
  - Interactive policy controls
  - Comparison and export features

## License

Created for the City of Delta Fast Track Program Focus Group.
© 2025 Dynamic Planning + Science & Western Spaces

---

**Next Meeting:** Use this tool to explore scenarios and build consensus on final policy recommendations.
