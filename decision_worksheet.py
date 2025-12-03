"""
Delta Fast Track Decision Worksheet
A simplified tool for focus group members to compare policy options and submit preferences.
"""

import streamlit as st
from dataclasses import dataclass
from typing import Dict, List
import urllib.parse

# ============================================================================
# REUSE CALCULATION CLASSES FROM SIMULATOR
# ============================================================================

@dataclass
class ProjectParams:
    """Parameters for a development project"""
    base_units: int = 4
    construction_cost_per_unit: float = 200000
    land_dev_value_per_unit: float = 35000
    market_rent_1br: float = 1211
    market_rent_2br: float = 1425
    market_rent_3br: float = 1710
    unit_mix: dict = None
    market_sale_price: float = 334000
    construction_valuation: float = None  # Will be calculated based on units

    def __post_init__(self):
        if self.unit_mix is None:
            self.unit_mix = {'1BR': 0.20, '2BR': 0.60, '3BR': 0.20}
        if self.construction_valuation is None:
            self.construction_valuation = self.base_units * self.construction_cost_per_unit

    def get_weighted_market_rent(self) -> float:
        market_rents = {'1BR': self.market_rent_1br, '2BR': self.market_rent_2br, '3BR': self.market_rent_3br}
        return sum(market_rents[br] * self.unit_mix[br] for br in self.unit_mix if br in market_rents)


@dataclass
class PolicySettings:
    """Fast Track policy levers"""
    affordability_period_years: int = 15
    rental_ami_threshold: float = 0.80
    min_affordable_pct: float = 0.25
    density_bonus_pct: float = 0.20
    bonus_affordable_req: float = 0.50
    waive_planning_fees: bool = True
    waive_building_permit: bool = True
    tap_fee_reduction_pct: float = 0.60
    use_tax_rebate_pct: float = 0.50
    fast_track_time_value: float = 50000


@dataclass
class AMI_Data:
    """2025 Delta County AMI data"""
    chfa_rents_by_bedroom = {
        0.60: {'1BR': 1147, '2BR': 1377, '3BR': 1591},
        0.70: {'1BR': 1338, '2BR': 1606, '3BR': 1856},
        0.80: {'1BR': 1530, '2BR': 1836, '3BR': 2122},
        0.90: {'1BR': 1721, '2BR': 2065, '3BR': 2387},
        1.00: {'1BR': 1912, '2BR': 2295, '3BR': 2652},
    }

    def get_weighted_affordable_rent(self, ami_pct: float, unit_mix: dict) -> float:
        if ami_pct not in self.chfa_rents_by_bedroom:
            rents = {br: ami_pct * self.chfa_rents_by_bedroom[1.00][br] for br in ['1BR', '2BR', '3BR']}
        else:
            rents = self.chfa_rents_by_bedroom[ami_pct]
        return sum(rents[br] * unit_mix[br] for br in unit_mix if br in rents)


class FeeCalculator:
    """Calculate City of Delta fees"""

    @staticmethod
    def building_permit_fee(valuation: float) -> float:
        if valuation <= 1000000:
            fee = 3233.75 + ((valuation - 500000) / 1000) * 4.75 if valuation > 500000 else 993.75 + ((valuation - 100000) / 1000) * 5.60
        else:
            fee = 5608.75 + ((valuation - 1000000) / 1000) * 3.15
        return max(fee, 0)

    @staticmethod
    def tap_and_system_fees(num_units: int) -> float:
        # Simplified: scale based on units
        # Small projects use smaller taps
        if num_units <= 6:
            water_bsif = 3000 + (1500 * max(0, num_units - 1))
            water_tap = 1680
            sewer = 5450 + (2600 * max(0, num_units - 1))
        else:
            water_bsif = 86100 + (1500 * max(0, num_units - 1))
            water_tap = 12420
            sewer = 154000 + (2600 * max(0, num_units - 1))
        return water_bsif + water_tap + sewer

    @staticmethod
    def use_tax(materials_cost: float) -> float:
        return materials_cost * 0.03

    @staticmethod
    def planning_fees(num_units: int) -> float:
        return 500 + (num_units * 20) + 250  # Preliminary + Final plat


def calculate_scenario(project: ProjectParams, policy: PolicySettings) -> Dict:
    """Calculate all metrics for a given scenario"""
    ami = AMI_Data()
    fees = FeeCalculator()

    # Unit calculations
    bonus_units = int(project.base_units * policy.density_bonus_pct)
    total_units = project.base_units + bonus_units
    base_affordable = int(project.base_units * policy.min_affordable_pct)
    bonus_affordable = int(bonus_units * policy.bonus_affordable_req)
    total_affordable = base_affordable + bonus_affordable
    market_rate_units = total_units - total_affordable

    # Fee calculations
    planning_fee = fees.planning_fees(total_units) if policy.waive_planning_fees else 0
    building_permit = fees.building_permit_fee(project.construction_valuation) if policy.waive_building_permit else 0
    tap_fees_full = fees.tap_and_system_fees(total_units)
    tap_fee_savings = tap_fees_full * policy.tap_fee_reduction_pct
    materials_cost = project.construction_valuation * 0.60
    use_tax_savings = fees.use_tax(materials_cost) * policy.use_tax_rebate_pct

    total_fee_waivers = planning_fee + building_permit + tap_fee_savings + use_tax_savings

    # Density bonus value
    density_bonus_value = bonus_units * (project.construction_cost_per_unit + project.land_dev_value_per_unit)

    # Developer costs (rent gap over time)
    market_rent = project.get_weighted_market_rent()
    affordable_rent = ami.get_weighted_affordable_rent(policy.rental_ami_threshold, project.unit_mix)
    monthly_rent_gap = market_rent - affordable_rent
    total_rent_impact = monthly_rent_gap * total_affordable * 12 * policy.affordability_period_years

    # Net position
    total_benefits = density_bonus_value + total_fee_waivers + policy.fast_track_time_value
    net_developer_gain = total_benefits - total_rent_impact

    # City metrics
    unit_years = total_affordable * policy.affordability_period_years
    cost_per_unit_year = total_fee_waivers / unit_years if unit_years > 0 else 0

    return {
        'total_units': total_units,
        'bonus_units': bonus_units,
        'affordable_units': total_affordable,
        'market_rate_units': market_rate_units,
        'fee_waivers': total_fee_waivers,
        'density_bonus_value': density_bonus_value,
        'total_benefits': total_benefits,
        'rent_impact': total_rent_impact,
        'net_developer_gain': net_developer_gain,
        'adds_value': net_developer_gain > 0,
        'unit_years': unit_years,
        'cost_per_unit_year': cost_per_unit_year,
        'affordability_years': policy.affordability_period_years,
    }


# ============================================================================
# DEFINE THE 4 SCENARIOS
# ============================================================================

SCENARIOS = {
    'none': {
        'name': 'No Fast Track',
        'tagline': 'Status quo - no Prop 123 participation',
        'color': '#6c757d',
        'policy': None,  # Special case
    },
    'light': {
        'name': 'Light Touch',
        'tagline': '15 years, modest incentives',
        'color': '#17a2b8',
        'policy': PolicySettings(
            affordability_period_years=15,
            density_bonus_pct=0.10,
            bonus_affordable_req=0.50,
            waive_planning_fees=True,
            waive_building_permit=True,
            tap_fee_reduction_pct=0.0,
            use_tax_rebate_pct=0.0,
        ),
    },
    'middle': {
        'name': 'Middle Ground',
        'tagline': '15 years, full incentives',
        'color': '#28a745',
        'policy': PolicySettings(
            affordability_period_years=15,
            density_bonus_pct=0.20,
            bonus_affordable_req=0.50,
            waive_planning_fees=True,
            waive_building_permit=True,
            tap_fee_reduction_pct=0.60,
            use_tax_rebate_pct=0.50,
        ),
    },
    'maximum': {
        'name': 'Maximum Commitment',
        'tagline': '30 years, full incentives',
        'color': '#fd7e14',
        'policy': PolicySettings(
            affordability_period_years=30,
            density_bonus_pct=0.20,
            bonus_affordable_req=0.50,
            waive_planning_fees=True,
            waive_building_permit=True,
            tap_fee_reduction_pct=0.60,
            use_tax_rebate_pct=0.50,
        ),
    },
}


# ============================================================================
# MAIN APP
# ============================================================================

def main():
    st.set_page_config(
        page_title="Delta Fast Track - Decision Worksheet",
        page_icon="🏠",
        layout="wide"
    )

    # Custom CSS for clean, simple look
    st.markdown("""
    <style>
    .main-header {
        text-align: center;
        padding: 1rem;
        background: linear-gradient(135deg, #1e3a5f 0%, #2c5282 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .scenario-card {
        border: 2px solid #e0e0e0;
        border-radius: 10px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        background: white;
    }
    .scenario-card h3 {
        margin-top: 0;
    }
    .metric-row {
        display: flex;
        justify-content: space-between;
        padding: 0.5rem 0;
        border-bottom: 1px solid #f0f0f0;
    }
    .metric-label {
        color: #666;
    }
    .metric-value {
        font-weight: bold;
    }
    .good { color: #28a745; }
    .neutral { color: #6c757d; }
    .caution { color: #fd7e14; }
    .project-box {
        background: #f8f9fa;
        border-left: 4px solid #1e3a5f;
        padding: 1rem;
        margin: 1rem 0;
    }
    .ranking-section {
        background: #fff3cd;
        border: 2px solid #ffc107;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 2rem 0;
    }
    .stSelectbox > div > div {
        font-size: 1.1rem;
    }
    </style>
    """, unsafe_allow_html=True)

    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🏠 Delta Fast Track Decision Worksheet</h1>
        <p style="font-size: 1.2rem; margin-bottom: 0;">Compare your options and share your preference</p>
    </div>
    """, unsafe_allow_html=True)

    # Introduction
    st.markdown("""
    ### The Question We're Answering

    **Should Delta participate in Prop 123's Fast Track program?** If so, what should the incentives look like?

    Below you'll see **4 options** applied to real project examples. Review them, then **rank your preferences** at the bottom.
    """)

    # Project size selector
    st.markdown("---")
    col1, col2 = st.columns([2, 3])
    with col1:
        st.markdown("### Example Project Size")
        project_size = st.radio(
            "Choose a project size to see the numbers:",
            ["Small (4 units)", "Medium (10 units)"],
            index=0,
            help="The same policy options applied to different project sizes"
        )

    with col2:
        if "4 units" in project_size:
            st.markdown("""
            <div class="project-box">
            <strong>Small Project: 4-Unit Rental Building</strong><br>
            Think of a local builder putting up two duplexes on Main Street.<br>
            Construction cost: ~$800,000 | Current fees: ~$15,000
            </div>
            """, unsafe_allow_html=True)
            project = ProjectParams(base_units=4)
        else:
            st.markdown("""
            <div class="project-box">
            <strong>Medium Project: 10-Unit Apartment Building</strong><br>
            A small apartment complex, like what might go on 7th Street.<br>
            Construction cost: ~$2,000,000 | Current fees: ~$300,000+
            </div>
            """, unsafe_allow_html=True)
            project = ProjectParams(base_units=10)

    st.markdown("---")

    # Calculate all scenarios
    results = {}
    for key, scenario in SCENARIOS.items():
        if scenario['policy'] is None:
            # No Fast Track baseline
            results[key] = {
                'total_units': project.base_units,
                'bonus_units': 0,
                'affordable_units': 0,
                'market_rate_units': project.base_units,
                'fee_waivers': 0,
                'density_bonus_value': 0,
                'total_benefits': 0,
                'rent_impact': 0,
                'net_developer_gain': 0,
                'adds_value': None,
                'unit_years': 0,
                'cost_per_unit_year': 0,
                'affordability_years': 0,
            }
        else:
            results[key] = calculate_scenario(project, scenario['policy'])

    # Display scenarios as comparison cards
    st.markdown("### Compare Your Options")

    cols = st.columns(4)
    scenario_keys = ['none', 'light', 'middle', 'maximum']

    for i, key in enumerate(scenario_keys):
        scenario = SCENARIOS[key]
        r = results[key]

        with cols[i]:
            # Card header with color
            st.markdown(f"""
            <div style="background: {scenario['color']}; color: white; padding: 1rem; border-radius: 10px 10px 0 0; text-align: center;">
                <h3 style="margin: 0; color: white;">{scenario['name']}</h3>
                <small>{scenario['tagline']}</small>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("""<div style="border: 2px solid #e0e0e0; border-top: none; border-radius: 0 0 10px 10px; padding: 1rem; background: white; min-height: 400px;">""", unsafe_allow_html=True)

            if key == 'none':
                st.markdown("**What the builder gets:**")
                st.markdown("- No bonus units")
                st.markdown("- Pays all fees")
                st.markdown("- Standard timeline")
                st.markdown("")
                st.markdown("**What the city gets:**")
                st.markdown("- Full fee revenue")
                st.markdown("- No affordable units guaranteed")
                st.markdown("")
                st.markdown("**What residents get:**")
                st.markdown("- Market-rate housing only")
                st.markdown("")
                st.markdown("---")
                st.markdown("*No cost, no guaranteed benefit*")
            else:
                policy = scenario['policy']

                st.markdown("**What the builder gets:**")
                st.markdown(f"- **{r['bonus_units']} extra units** to build")
                st.markdown(f"- **${r['fee_waivers']:,.0f}** in fee savings")
                if r['adds_value']:
                    st.markdown(f"- ✅ **Worth it** (${r['net_developer_gain']:,.0f} net gain)")
                else:
                    st.markdown(f"- ⚠️ May not pencil (${r['net_developer_gain']:,.0f})")

                st.markdown("")
                st.markdown("**What the city gives up:**")
                st.markdown(f"- **${r['fee_waivers']:,.0f}** in waived fees")
                st.markdown(f"- ${r['cost_per_unit_year']:,.0f}/family/year")

                st.markdown("")
                st.markdown("**What residents get:**")
                st.markdown(f"- **{r['affordable_units']} affordable units**")
                st.markdown(f"- For **{r['affordability_years']} years**")
                st.markdown(f"- ({r['unit_years']} family-years total)")

            st.markdown("</div>", unsafe_allow_html=True)

    # Summary comparison table
    st.markdown("---")
    st.markdown("### Quick Comparison")

    comparison_data = []
    for key in scenario_keys:
        r = results[key]
        scenario = SCENARIOS[key]
        comparison_data.append({
            'Option': scenario['name'],
            'Extra Units': r['bonus_units'],
            'Affordable Units': r['affordable_units'],
            'Years Affordable': r['affordability_years'] if r['affordability_years'] > 0 else '-',
            'City Waives': f"${r['fee_waivers']:,.0f}" if r['fee_waivers'] > 0 else '-',
            'Builder Net Gain': f"${r['net_developer_gain']:,.0f}" if key != 'none' else '-',
            'Worth It?': '✅ Yes' if r['adds_value'] else ('N/A' if r['adds_value'] is None else '⚠️ Maybe not'),
        })

    st.table(comparison_data)

    # Important context
    st.markdown("""
    <div style="background: #e7f3ff; border-left: 4px solid #2196F3; padding: 1rem; margin: 1rem 0;">
    <strong>💡 Important Context</strong><br>
    At 80% AMI, the state-allowed rent ($1,836/month for a 2BR) is actually <em>higher</em> than Delta's current market rent ($1,425/month).
    This means developers can charge <em>more</em> for affordable units than market units - making longer affordability periods more attractive, not less.
    </div>
    """, unsafe_allow_html=True)

    # Ranking section
    st.markdown("---")
    st.markdown("""
    <div class="ranking-section">
    <h2 style="margin-top: 0;">📋 Your Ranking</h2>
    <p>Please rank the options from your <strong>1st choice</strong> (best) to <strong>4th choice</strong> (least preferred).</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        name = st.text_input("Your name:", placeholder="Enter your name")

        rank_1 = st.selectbox(
            "🥇 1st Choice (Best option):",
            ["-- Select --", "No Fast Track", "Light Touch", "Middle Ground", "Maximum Commitment"],
            index=0
        )
        rank_2 = st.selectbox(
            "🥈 2nd Choice:",
            ["-- Select --", "No Fast Track", "Light Touch", "Middle Ground", "Maximum Commitment"],
            index=0
        )

    with col2:
        role = st.selectbox(
            "Your perspective:",
            ["-- Select --", "Taxpayer/Resident", "Developer/Builder", "City Staff", "Elected Official", "Other"]
        )

        rank_3 = st.selectbox(
            "🥉 3rd Choice:",
            ["-- Select --", "No Fast Track", "Light Touch", "Middle Ground", "Maximum Commitment"],
            index=0
        )
        rank_4 = st.selectbox(
            "4th Choice (Least preferred):",
            ["-- Select --", "No Fast Track", "Light Touch", "Middle Ground", "Maximum Commitment"],
            index=0
        )

    comments = st.text_area(
        "Any comments or concerns? (Optional)",
        placeholder="What questions do you have? What would help you decide?",
        height=100
    )

    # Validation
    rankings = [rank_1, rank_2, rank_3, rank_4]
    selected_rankings = [r for r in rankings if r != "-- Select --"]

    valid = True
    if len(selected_rankings) != len(set(selected_rankings)):
        st.warning("⚠️ Please select each option only once.")
        valid = False
    if len(selected_rankings) < 4:
        st.info("Please rank all 4 options.")
        valid = False
    if not name:
        valid = False
    if role == "-- Select --":
        valid = False

    # Submit button
    st.markdown("---")

    if valid:
        # Build email content
        email_subject = f"Delta Fast Track Preference - {name}"
        email_body = f"""Delta Fast Track Decision Worksheet Response

Name: {name}
Role: {role}
Project Size Reviewed: {project_size}

RANKINGS:
1st Choice: {rank_1}
2nd Choice: {rank_2}
3rd Choice: {rank_3}
4th Choice: {rank_4}

COMMENTS:
{comments if comments else '(None provided)'}

---
Submitted via Delta Fast Track Decision Worksheet
"""

        # URL encode for mailto
        encoded_subject = urllib.parse.quote(email_subject)
        encoded_body = urllib.parse.quote(email_body)
        mailto_link = f"mailto:sarah@westernspaces.co?subject={encoded_subject}&body={encoded_body}"

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown(f"""
            <a href="{mailto_link}" style="display: block; text-align: center; background: #28a745; color: white; padding: 1rem 2rem; border-radius: 10px; text-decoration: none; font-size: 1.2rem; font-weight: bold;">
            📧 Submit My Preference
            </a>
            <p style="text-align: center; color: #666; margin-top: 0.5rem;">
            This will open your email app with your response ready to send.
            </p>
            """, unsafe_allow_html=True)
    else:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("""
            <div style="text-align: center; background: #e0e0e0; color: #666; padding: 1rem 2rem; border-radius: 10px; font-size: 1.2rem;">
            📧 Submit My Preference
            </div>
            <p style="text-align: center; color: #666; margin-top: 0.5rem;">
            Please complete all fields above to submit.
            </p>
            """, unsafe_allow_html=True)

    # Print version
    st.markdown("---")
    st.markdown("### 🖨️ Need a Paper Copy?")

    # Generate printable HTML
    print_html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Delta Fast Track Decision Worksheet</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
        h1 {{ text-align: center; color: #1e3a5f; }}
        .intro {{ background: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
        th {{ background: #1e3a5f; color: white; }}
        .ranking-box {{ border: 2px solid #ffc107; padding: 20px; margin: 20px 0; background: #fff3cd; }}
        .rank-line {{ margin: 15px 0; font-size: 1.1rem; }}
        .checkbox {{ width: 20px; height: 20px; border: 2px solid #333; display: inline-block; margin-right: 10px; }}
        .comment-box {{ border: 1px solid #ccc; min-height: 100px; margin: 10px 0; padding: 10px; }}
        @media print {{ body {{ padding: 0; }} }}
    </style>
</head>
<body>
    <h1>🏠 Delta Fast Track Decision Worksheet</h1>

    <div class="intro">
        <strong>The Question:</strong> Should Delta participate in Prop 123's Fast Track program? If so, what should the incentives look like?
    </div>

    <h2>Compare Your Options ({project_size})</h2>

    <table>
        <tr>
            <th>Option</th>
            <th>Extra Units</th>
            <th>Affordable Units</th>
            <th>Years</th>
            <th>City Waives</th>
            <th>Builder Gain</th>
        </tr>
        <tr>
            <td><strong>No Fast Track</strong><br><small>Status quo</small></td>
            <td>0</td>
            <td>0</td>
            <td>-</td>
            <td>-</td>
            <td>-</td>
        </tr>
        <tr>
            <td><strong>Light Touch</strong><br><small>15 yrs, modest</small></td>
            <td>{results['light']['bonus_units']}</td>
            <td>{results['light']['affordable_units']}</td>
            <td>15</td>
            <td>${results['light']['fee_waivers']:,.0f}</td>
            <td>${results['light']['net_developer_gain']:,.0f}</td>
        </tr>
        <tr>
            <td><strong>Middle Ground</strong><br><small>15 yrs, full</small></td>
            <td>{results['middle']['bonus_units']}</td>
            <td>{results['middle']['affordable_units']}</td>
            <td>15</td>
            <td>${results['middle']['fee_waivers']:,.0f}</td>
            <td>${results['middle']['net_developer_gain']:,.0f}</td>
        </tr>
        <tr>
            <td><strong>Maximum</strong><br><small>30 yrs, full</small></td>
            <td>{results['maximum']['bonus_units']}</td>
            <td>{results['maximum']['affordable_units']}</td>
            <td>30</td>
            <td>${results['maximum']['fee_waivers']:,.0f}</td>
            <td>${results['maximum']['net_developer_gain']:,.0f}</td>
        </tr>
    </table>

    <div class="ranking-box">
        <h2 style="margin-top: 0;">Your Ranking</h2>
        <p>Rank from 1st (best) to 4th (least preferred):</p>

        <div class="rank-line">
            <strong>Name:</strong> _________________________________
            <strong>Role:</strong> _________________________________
        </div>

        <div class="rank-line">🥇 <strong>1st Choice:</strong> _________________________________</div>
        <div class="rank-line">🥈 <strong>2nd Choice:</strong> _________________________________</div>
        <div class="rank-line">🥉 <strong>3rd Choice:</strong> _________________________________</div>
        <div class="rank-line">4th <strong>Choice:</strong> _________________________________</div>

        <div style="margin-top: 20px;">
            <strong>Comments or concerns:</strong>
            <div class="comment-box"></div>
        </div>
    </div>

    <p style="text-align: center; color: #666; font-size: 0.9rem;">
        Return completed worksheet to Sarah at sarah@westernspaces.co or bring to the next focus group meeting.
    </p>
</body>
</html>
"""

    st.download_button(
        label="📄 Download Printable Worksheet (HTML)",
        data=print_html,
        file_name="delta_fast_track_worksheet.html",
        mime="text/html"
    )

    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; font-size: 0.9rem;">
        <p>Want to explore more scenarios? Use the <a href="https://delta-fast-track-simulator-qrzf2t87mqwzfgwporenqz.streamlit.app" target="_blank">Full Simulator</a></p>
        <p>Questions? Contact Sarah at sarah@westernspaces.co</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
