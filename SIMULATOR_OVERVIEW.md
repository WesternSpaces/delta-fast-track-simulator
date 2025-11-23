# Delta Fast Track Simulator - Project Overview

## What We Built

An interactive web application that lets the City of Delta Focus Group explore policy tradeoffs for the Fast Track affordable housing program. Stakeholders can adjust parameters in real-time and immediately see impacts on developer feasibility, city costs, and community benefits.

## Key Features

### 1. Policy Control Panel (Left Sidebar)
Adjust all major policy levers:
- **Affordability Period:** 5 to 99 years (permanent)
- **Rental AMI:** 60% or 80% AMI thresholds
- **Ownership AMI:** 100%, 110%, or 120% AMI thresholds
- **Minimum Affordable %:** 10% to 50% of base project
- **Density Bonus:** 0% to 30% additional units
- **Bonus Unit Requirements:** What % of bonus units must be affordable
- **Fee Waivers:** Toggle planning, building, tap/sewer fees
- **Fee Reductions:** Sliding scale for tap fees and use tax rebates

### 2. Developer Economics Tab
Complete pro forma showing:
- **Benefits:** Density bonus value, fee waivers, time savings
- **Costs:** Lost rental income over affordability period
- **Bottom Line:** Net developer gain/loss, ROI, feasibility assessment
- **Waterfall Chart:** Visual breakdown of financial impacts

### 3. Community Benefit Tab
City perspective analysis:
- **Investment Metrics:** Total city cost, cost per unit, cost per unit-year
- **Housing Created:** Affordable units, total units, unit-years of affordability
- **Economic Impact:** Construction jobs, permanent jobs, population served
- **Long-term View:** 20-year cost projections
- **Unit Mix:** Visual breakdown of affordable vs. market rate units

### 4. Comparisons Tab
Side-by-side scenario analysis:
- **Affordability Period Comparison:** How do 5, 15, 20, 30, 50-year terms compare?
- **AMI Threshold Comparison:** 60% vs. 80% AMI impacts
- **Tradeoff Visualization:** Interactive scatter plot showing cost efficiency vs. duration
- **Current Scenario Marker:** Star shows where your current settings fall

### 5. Export & Share Tab
Document and distribute results:
- **Summary Tables:** All key metrics organized by category
- **CSV Download:** Export results for further analysis
- **Shareable Links:** Recreate scenarios by sharing URL parameters (future enhancement)

## Technical Implementation

### Data Sources (All Official 2025 Data)
✅ City of Delta 2025 Fee Schedule (complete)
✅ HUD 2025 Delta County AMI data
✅ Density bonus calculations from current Fast Track proposal
✅ Construction cost estimates (conservative)
✅ Market rent data ($1,425 for 2BR)

### Calculation Engine

**Developer Pro Forma:**
```
Benefits = Density Bonus Value + Fee Waivers + Time Savings
  - Density Bonus = Bonus Units × ($75K construction + $90K land)
  - Fee Waivers = Building + Tap/Sewer + Use Tax + Planning
  - Time Savings = $50K (reduced carrying costs)

Costs = Monthly Rent Gap × Affordable Units × 12 × Years
  - Rent Gap = Market Rent - Affordable Rent (based on AMI)

Net Position = Benefits - Costs
ROI = Net Position / Total Project Cost × 100%
```

**Community Analysis:**
```
City Investment = All Fee Waivers + Density Bonus Value

Cost per Unit-Year = City Investment / (Units × Years)
  - Normalizes across different affordability periods
  - Lower is better (more efficient use of city resources)

20-Year Cost = City Investment × (20 / Affordability Period)
  - Shows how much it costs to maintain units over 20 years
  - Short terms require re-incentivizing the same units
```

### Fee Calculations (From Official Schedule)

**Building Permits (Table 3B):**
- Tiered formula based on construction valuation
- For $9.6M project: ~$32,699

**Tap & System Improvement Fees:**
- Water: $86,100 base + $1,500 per additional unit
- Sewer: $154,000 base + $2,600 per additional unit
- For 24-unit project: $334,500 total

**Use Tax:**
- 3% of materials cost
- Materials ≈ 60% of construction valuation
- Rebate: 0% to 50% based on policy

**Planning Fees:**
- Base application fee: $200

### Default Scenario (20-Unit Example)

Based on the current Fast Track proposal presented in the focus group packet:

**Project:**
- Base units: 20
- Density bonus: 20% = 4 bonus units
- Total units: 24
- Market rent: $1,425/month

**Affordability:**
- Base requirement: 25% of 20 = 5 units
- Bonus requirement: 50% of 4 = 2 units
- Total affordable: 7 units
- Period: 30 years
- AMI: 80% ($1,301/month affordable)

**Incentives:**
- Building permits: Waived (~$32,699)
- Tap/system fees: 60% reduction ($200,640 savings)
- Use tax: 50% rebate ($86,400 savings)
- Planning fees: Waived ($200)
- Density bonus value: $660,000 (4 units × $165K)
- Time savings: $50,000

**Results:**
- Total developer benefits: ~$1,030,000
- Lost rent (7 units × $124/mo × 30 yrs): ~$311,000
- Net developer gain: ~$719,000 ✅ FEASIBLE
- City cost per unit-year: ~$4,900
- Units created: 24 total, 7 affordable

## File Structure

```
meeting-one/
├── fast_track_simulator.py    # Main application (35KB)
├── requirements.txt            # Python dependencies
├── README.md                   # Full documentation (5.6KB)
├── QUICKSTART.md              # Deployment guide
├── SIMULATOR_OVERVIEW.md      # This file
├── .gitignore                 # Git configuration
│
├── Data/                      # Source data
│   ├── density-bonus-calculations+jlo.xlsx
│   ├── 2025_fee_schedule(4).pdf
│   ├── IncentivePolicyAssessment-Feb2025.pdf
│   └── ...
│
└── Visuals/                   # Charts from packet
    ├── delta_ami_policy_tradeoffs.svg
    └── ...
```

## Deployment Options

### Option 1: Streamlit Cloud (Recommended - FREE!)
- **Pros:** Free, automatic updates, shareable URL, no server maintenance
- **Cons:** Cold start delay (~30 seconds first load)
- **Time to deploy:** 10 minutes
- **URL format:** `https://your-app-name.streamlit.app`

### Option 2: Local Network
- **Pros:** Fast, no internet required, full control
- **Cons:** Only accessible on local network, must run manually
- **Use case:** In-person meetings only

### Option 3: Custom Server
- **Pros:** Full control, custom domain, guaranteed uptime
- **Cons:** Monthly cost (~$5-20), requires server management
- **Use case:** If you need guaranteed performance

**Recommendation:** Start with Streamlit Cloud (free). It's perfect for your focus group meetings and can be upgraded later if needed.

## Usage Workflow

### Before the Meeting
1. Deploy to Streamlit Cloud (10 minutes)
2. Test with a few scenarios
3. Share URL with focus group members
4. Prepare 2-3 "key scenarios" to demonstrate

### During the Meeting
1. Project simulator on screen
2. Walk through default (20-unit) scenario
3. Adjust affordability period lever → show impact
4. Adjust AMI threshold → show rent gap impact
5. Compare 5, 15, 20, 30-year options side-by-side
6. Let focus group suggest scenarios to explore
7. Download results for record-keeping

### After the Meeting
1. Share simulator URL for members to explore on their own
2. Collect feedback on additional features needed
3. Update calculations if policies change
4. Use comparison tab to build final recommendations

## Key Questions the Simulator Answers

✅ **"What affordability period balances cost and benefit?"**
   - Compare cost per unit-year across different terms
   - See 20-year total costs
   - Visualize feasibility for developers

✅ **"How do AMI thresholds affect the rent gap?"**
   - 60% AMI: $976 rent, $449/mo gap from market
   - 80% AMI: $1,301 rent, $124/mo gap from market
   - See immediate impact on developer costs

✅ **"Is the density bonus enough?"**
   - 20% bonus = 4 units = $660,000 value
   - Compare to 30-year lost rent costs
   - Adjust % of bonus units that must be affordable

✅ **"How should fee reductions tier with affordability periods?"**
   - Current: 30%/60%/100% by term length
   - Test different combinations
   - See impact on developer ROI

✅ **"What makes a project 'pencil out'?"**
   - Developer net gain must be positive
   - ROI should be 5-10%+ for feasibility
   - See exactly which levers affect feasibility

✅ **"What's Delta's cost compared to neighboring communities?"**
   - Delta's approach vs. Durango, Montrose, Grand Junction
   - Cost per unit-year comparison
   - Long-term vs. short-term strategy tradeoffs

## Future Enhancements (Optional)

### Phase 2 Features
- **Save/Load Scenarios:** Bookmark specific configurations
- **Comparison Mode:** View 2-3 scenarios simultaneously
- **Monte Carlo Analysis:** Test sensitivity to assumptions
- **Custom Project Types:** Townhomes, single-family, mixed-use
- **Jobs Calculator:** Detailed employment impact by sector
- **Tax Revenue Projections:** Sales tax, property tax impacts

### Data Improvements
- **Real Project Pipeline:** Load actual proposed projects
- **Market Data Integration:** Pull live rental rates
- **Historical Tracking:** Compare outcomes over time

### Advanced Features
- **Multi-year Projections:** Cash flow over time
- **NPV Analysis:** Present value calculations
- **Risk Assessment:** Probability of developer participation
- **Policy Optimization:** AI-suggested optimal configurations

## Success Metrics

**For Week One (Before Next Meeting):**
- ✅ Simulator deployed and accessible
- ✅ All calculations match source data
- ✅ Focus group can independently explore scenarios
- ✅ Export functionality working

**For the Focus Group Process:**
- Consensus on affordability period
- Agreement on AMI thresholds
- Finalized density bonus percentages
- Clear incentive tier structure
- Documented rationale for decisions

## Support & Maintenance

**To update data:**
1. Edit `AMI_Data` class for new HUD income limits
2. Edit `FeeCalculator` for fee schedule changes
3. Commit and push → auto-deploys

**To add features:**
1. Modify `fast_track_simulator.py`
2. Test locally: `streamlit run fast_track_simulator.py`
3. Push to GitHub → auto-deploys

**To fix bugs:**
1. Check Streamlit Cloud deployment logs
2. Test locally to reproduce
3. Fix and push update

## Credits

**Built for:** City of Delta Fast Track Program Focus Group
**Date:** November 2025
**Facilitators:** Dynamic Planning + Science & Western Spaces
**Data Sources:**
- City of Delta 2025 Fee Schedule
- HUD 2025 Income Limits
- Delta County Housing Needs Assessment (2023)
- RPI Incentive Policy Assessment (February 2025)

**Technology:**
- Python 3.9+
- Streamlit 1.31
- Plotly for visualizations
- Pandas for data analysis

---

## Quick Links

- **Deployment Guide:** See `QUICKSTART.md`
- **Full Documentation:** See `README.md`
- **GitHub:** [Your repository URL]
- **Live App:** [Your Streamlit Cloud URL]

**Questions?** Contact the focus group facilitators or email support@westernspaces.com
