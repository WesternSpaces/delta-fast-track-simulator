"""
City of Delta Fast Track Incentive Tradeoff Simulator
Interactive tool for exploring policy decisions on affordability period, AMI thresholds,
density bonuses, and fee waivers.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from dataclasses import dataclass
from typing import Dict, List, Tuple

# ============================================================================
# DATA CLASSES AND CALCULATION ENGINE
# ============================================================================

@dataclass
class ProjectParams:
    """Parameters for a development project"""
    base_units: int = 20
    construction_cost_per_unit: float = 75000  # Conservative estimate
    land_dev_value_per_unit: float = 90000
    market_rent_2br: float = 1425  # Current Delta market
    construction_valuation: float = 9600000  # For fee calculations

@dataclass
class PolicySettings:
    """Fast Track policy levers"""
    # Affordability requirements
    affordability_period_years: int = 30
    rental_ami_threshold: float = 0.80  # 60% or 80%
    ownership_ami_threshold: float = 1.00  # 100%, 110%, or 120%
    min_affordable_pct: float = 0.25  # 25% of original units

    # Density bonus
    density_bonus_pct: float = 0.20  # Up to 20%
    bonus_affordable_req: float = 0.50  # 50% of bonus units must be affordable

    # Fee waivers and reductions
    waive_planning_fees: bool = True
    waive_building_permit: bool = True
    waive_park_fees: bool = True
    tap_fee_reduction_pct: float = 0.60  # 30%, 60%, or 100% based on term
    use_tax_rebate_pct: float = 0.50  # 50% rebate

    # Time savings
    fast_track_time_value: float = 50000  # Reduced carrying costs

@dataclass
class AMI_Data:
    """2025 Delta County AMI data"""
    ami_60_2person: float = 39020
    ami_80_2person: float = 52050
    ami_100_2person: float = 65100
    ami_110_2person: float = 71610
    ami_120_2person: float = 78120

    def get_affordable_rent(self, ami_pct: float) -> float:
        """Calculate affordable rent at given AMI percentage (2-person HH)"""
        if ami_pct == 0.60:
            income = self.ami_60_2person
        elif ami_pct == 0.80:
            income = self.ami_80_2person
        elif ami_pct == 1.00:
            income = self.ami_100_2person
        elif ami_pct == 1.10:
            income = self.ami_110_2person
        elif ami_pct == 1.20:
            income = self.ami_120_2person
        else:
            # Linear interpolation for other values
            income = ami_pct * self.ami_100_2person

        return (income * 0.30) / 12  # 30% of monthly income

    def get_affordable_purchase_price(self, ami_pct: float) -> float:
        """Estimate affordable purchase price at given AMI"""
        # Using standard mortgage qualifications
        # Rough estimate: ~4x annual income
        if ami_pct == 1.00:
            return 256000
        elif ami_pct == 1.10:
            return 281000
        elif ami_pct == 1.20:
            return 307000
        else:
            return ami_pct * 256000


class FeeCalculator:
    """Calculate City of Delta fees based on 2025 fee schedule"""

    @staticmethod
    def building_permit_fee(valuation: float) -> float:
        """Calculate building permit fee from Table 3B"""
        if valuation <= 500:
            return 23.50
        elif valuation <= 2000:
            return 23.50 + ((valuation - 500) / 100) * 3.05
        elif valuation <= 25000:
            return 69.25 + ((valuation - 2000) / 1000) * 14.00
        elif valuation <= 50000:
            return 391.25 + ((valuation - 25000) / 1000) * 10.10
        elif valuation <= 100000:
            return 643.75 + ((valuation - 50000) / 1000) * 7.00
        elif valuation <= 500000:
            return 993.75 + ((valuation - 100000) / 1000) * 5.60
        elif valuation <= 1000000:
            return 3233.75 + ((valuation - 500000) / 1000) * 4.75
        else:
            return 5608.75 + ((valuation - 1000000) / 1000) * 3.15

    @staticmethod
    def tap_and_system_fees(num_units: int, tap_size: str = "4_combo") -> float:
        """Calculate water/sewer tap and system improvement fees"""
        # Based on 24-unit apartment example with 4" combo domestic/fire tap
        # Water: $86,100 base + $1,500 per unit after first
        # Sewer: $154,000 base + $2,600 per unit after first

        if tap_size == "4_combo":
            water_base = 86100
            water_per_unit = 1500
            sewer_base = 154000
            sewer_per_unit = 2600
        else:
            # Default calculation
            water_base = 3000
            water_per_unit = 1500
            sewer_base = 5450
            sewer_per_unit = 2600

        water_total = water_base + (water_per_unit * max(0, num_units - 1))
        sewer_total = sewer_base + (sewer_per_unit * max(0, num_units - 1))

        return water_total + sewer_total

    @staticmethod
    def use_tax(materials_cost: float, rebate_pct: float = 0.0) -> float:
        """Calculate 3% use tax on materials, minus any rebate"""
        tax = materials_cost * 0.03
        return tax * (1 - rebate_pct)

    @staticmethod
    def planning_application_fee() -> float:
        """Base planning application fees"""
        return 200.0  # Variance example from fee schedule


class DeveloperProForma:
    """Calculate developer costs and benefits"""

    def __init__(self, project: ProjectParams, policy: PolicySettings, ami: AMI_Data):
        self.project = project
        self.policy = policy
        self.ami = ami
        self.fees = FeeCalculator()

    def calculate(self) -> Dict:
        """Run complete pro forma analysis"""

        # Unit calculations
        bonus_units = int(self.project.base_units * self.policy.density_bonus_pct)
        total_units = self.project.base_units + bonus_units

        # Affordable unit requirements
        base_affordable = int(self.project.base_units * self.policy.min_affordable_pct)
        bonus_affordable = int(bonus_units * self.policy.bonus_affordable_req)
        total_affordable = base_affordable + bonus_affordable
        market_rate_units = total_units - total_affordable

        # DEVELOPER BENEFITS

        # 1. Density bonus value
        density_bonus_value = bonus_units * (
            self.project.construction_cost_per_unit +
            self.project.land_dev_value_per_unit
        )

        # 2. Fee waivers
        planning_fees_waived = 0
        if self.policy.waive_planning_fees:
            planning_fees_waived = self.fees.planning_application_fee()

        building_permit_waived = 0
        if self.policy.waive_building_permit:
            building_permit_waived = self.fees.building_permit_fee(
                self.project.construction_valuation
            )

        tap_fees_full = self.fees.tap_and_system_fees(total_units)
        tap_fees_reduced = tap_fees_full * (1 - self.policy.tap_fee_reduction_pct)
        tap_fee_savings = tap_fees_full - tap_fees_reduced

        # Materials cost estimate (60% of construction valuation)
        materials_cost = self.project.construction_valuation * 0.60
        use_tax_savings = materials_cost * 0.03 * self.policy.use_tax_rebate_pct

        # Park fees (only for PUDs, set to 0 for apartments)
        park_fees_waived = 0

        total_fee_waivers = (planning_fees_waived + building_permit_waived +
                            tap_fee_savings + use_tax_savings + park_fees_waived)

        # 3. Time savings
        time_savings = self.policy.fast_track_time_value

        total_benefits = density_bonus_value + total_fee_waivers + time_savings

        # DEVELOPER COSTS

        # Lost rent from affordable units
        market_rent = self.project.market_rent_2br
        affordable_rent = self.ami.get_affordable_rent(self.policy.rental_ami_threshold)
        monthly_rent_gap = max(0, market_rent - affordable_rent)

        total_lost_rent = (monthly_rent_gap * total_affordable * 12 *
                          self.policy.affordability_period_years)

        # Net developer position
        net_developer_gain = total_benefits - total_lost_rent

        # ROI calculation
        total_project_cost = (total_units * self.project.construction_cost_per_unit +
                             total_units * self.project.land_dev_value_per_unit)
        roi_pct = (net_developer_gain / total_project_cost) * 100

        return {
            # Units
            'base_units': self.project.base_units,
            'bonus_units': bonus_units,
            'total_units': total_units,
            'base_affordable': base_affordable,
            'bonus_affordable': bonus_affordable,
            'total_affordable': total_affordable,
            'market_rate_units': market_rate_units,

            # Financial - Benefits
            'density_bonus_value': density_bonus_value,
            'planning_fees_waived': planning_fees_waived,
            'building_permit_waived': building_permit_waived,
            'tap_fee_savings': tap_fee_savings,
            'use_tax_savings': use_tax_savings,
            'park_fees_waived': park_fees_waived,
            'total_fee_waivers': total_fee_waivers,
            'time_savings': time_savings,
            'total_benefits': total_benefits,

            # Financial - Costs
            'market_rent': market_rent,
            'affordable_rent': affordable_rent,
            'monthly_rent_gap': monthly_rent_gap,
            'total_lost_rent': total_lost_rent,

            # Bottom line
            'net_developer_gain': net_developer_gain,
            'total_project_cost': total_project_cost,
            'roi_pct': roi_pct,
            'developer_feasible': net_developer_gain > 0
        }


class CommunityBenefitAnalysis:
    """Calculate community costs and benefits"""

    def __init__(self, dev_results: Dict, policy: PolicySettings):
        self.dev = dev_results
        self.policy = policy

    def calculate(self) -> Dict:
        """Analyze community perspective"""

        # City's investment
        city_investment = self.dev['total_benefits']

        # Affordable units gained
        affordable_units = self.dev['total_affordable']
        affordability_years = self.policy.affordability_period_years

        # Cost per unit metrics
        cost_per_unit_total = city_investment / affordable_units if affordable_units > 0 else 0
        cost_per_unit_per_year = cost_per_unit_total / affordability_years if affordability_years > 0 else 0

        # Unit-years of affordability
        unit_years = affordable_units * affordability_years
        cost_per_unit_year = city_investment / unit_years if unit_years > 0 else 0

        # 20-year projection
        if affordability_years > 0:
            cycles_in_20_years = 20 / affordability_years
            cost_20_year = city_investment * cycles_in_20_years
        else:
            cycles_in_20_years = 0
            cost_20_year = 0

        # Jobs impact (construction + permanent)
        construction_jobs = self.dev['total_units'] * 0.5  # Rough estimate
        permanent_jobs = self.dev['total_units'] * 0.1  # Property management, etc.

        return {
            'city_investment': city_investment,
            'affordable_units': affordable_units,
            'affordability_years': affordability_years,
            'cost_per_unit_total': cost_per_unit_total,
            'cost_per_unit_per_year': cost_per_unit_per_year,
            'unit_years': unit_years,
            'cost_per_unit_year': cost_per_unit_year,
            'cycles_in_20_years': cycles_in_20_years,
            'cost_20_year': cost_20_year,
            'construction_jobs': construction_jobs,
            'permanent_jobs': permanent_jobs,
        }


# ============================================================================
# STREAMLIT UI
# ============================================================================

def main():
    st.set_page_config(
        page_title="Delta Fast Track Simulator",
        page_icon="🏘️",
        layout="wide"
    )

    st.title("🏘️ City of Delta Fast Track Incentive Simulator")
    st.markdown("""
    Explore the tradeoffs between affordability period, density bonuses, AMI thresholds,
    and fee waivers. Adjust the policy levers below to see real-time impacts on developer
    feasibility and community benefit.
    """)

    # Initialize data
    ami_data = AMI_Data()

    # ========================================================================
    # SIDEBAR: POLICY CONTROLS
    # ========================================================================

    st.sidebar.header("⚙️ Policy Settings")

    st.sidebar.subheader("Affordability Requirements")

    affordability_period = st.sidebar.select_slider(
        "Affordability Period (years)",
        options=[5, 10, 15, 20, 30, 50, 99],
        value=30,
        help="Minimum years units must remain affordable. Current draft: 15 years. Neighbors: 30+ years."
    )
    affordability_display = "Permanent (99+ years)" if affordability_period == 99 else f"{affordability_period} years"

    rental_ami = st.sidebar.select_slider(
        "Rental AMI Threshold",
        options=[0.60, 0.80],
        value=0.80,
        format_func=lambda x: f"{int(x*100)}% AMI (${ami_data.get_affordable_rent(x):.0f}/mo)",
        help="Income limit for affordable rental units"
    )

    ownership_ami = st.sidebar.select_slider(
        "Ownership AMI Threshold",
        options=[1.00, 1.10, 1.20],
        value=1.00,
        format_func=lambda x: f"{int(x*100)}% AMI (${ami_data.get_affordable_purchase_price(x):,.0f})",
        help="Income limit for affordable for-sale units"
    )

    min_affordable_pct = st.sidebar.slider(
        "Minimum Affordable % (of base units)",
        min_value=0.10,
        max_value=0.50,
        value=0.25,
        step=0.05,
        format="%0.0f%%",
        help="Minimum percentage of original project that must be affordable"
    )

    st.sidebar.subheader("Density Bonus")

    density_bonus_pct = st.sidebar.slider(
        "Density Bonus Percentage",
        min_value=0.0,
        max_value=0.30,
        value=0.20,
        step=0.05,
        format="%0.0f%%",
        help="Additional units allowed beyond base zoning"
    )

    bonus_affordable_req = st.sidebar.slider(
        "% of Bonus Units that Must Be Affordable",
        min_value=0.0,
        max_value=1.0,
        value=0.50,
        step=0.10,
        format="%0.0f%%"
    )

    st.sidebar.subheader("Fee Waivers & Reductions")

    waive_planning = st.sidebar.checkbox("Waive Planning Application Fees", value=True)
    waive_building = st.sidebar.checkbox("Waive Building Permit Fees", value=True)

    tap_fee_reduction = st.sidebar.select_slider(
        "Tap & System Improvement Fee Reduction",
        options=[0.0, 0.30, 0.60, 1.00],
        value=0.60,
        format_func=lambda x: f"{int(x*100)}% reduction",
        help="Tier by affordability period: 20yr=30%, 30yr=60%, 50yr=100%"
    )

    use_tax_rebate = st.sidebar.slider(
        "Use Tax Rebate",
        min_value=0.0,
        max_value=0.50,
        value=0.50,
        step=0.10,
        format="%0.0f%%",
        help="Percentage of 3% materials use tax rebated"
    )

    # ========================================================================
    # PROJECT PARAMETERS (Advanced)
    # ========================================================================

    with st.sidebar.expander("🏗️ Project Parameters (Advanced)", expanded=False):
        base_units = st.number_input(
            "Base Project Size (units)",
            min_value=4,
            max_value=200,
            value=20,
            step=1
        )

        construction_cost = st.number_input(
            "Construction Cost per Unit",
            min_value=50000,
            max_value=150000,
            value=75000,
            step=5000,
            format="%d"
        )

        land_value = st.number_input(
            "Land/Development Value per Unit",
            min_value=30000,
            max_value=150000,
            value=90000,
            step=5000,
            format="%d"
        )

        market_rent = st.number_input(
            "Market Rent (2BR)",
            min_value=1000,
            max_value=2500,
            value=1425,
            step=25,
            format="%d"
        )

        construction_valuation = st.number_input(
            "Total Construction Valuation (for fees)",
            min_value=1000000,
            max_value=50000000,
            value=9600000,
            step=100000,
            format="%d"
        )

    # ========================================================================
    # RUN CALCULATIONS
    # ========================================================================

    project = ProjectParams(
        base_units=base_units,
        construction_cost_per_unit=construction_cost,
        land_dev_value_per_unit=land_value,
        market_rent_2br=market_rent,
        construction_valuation=construction_valuation
    )

    policy = PolicySettings(
        affordability_period_years=affordability_period,
        rental_ami_threshold=rental_ami,
        ownership_ami_threshold=ownership_ami,
        min_affordable_pct=min_affordable_pct,
        density_bonus_pct=density_bonus_pct,
        bonus_affordable_req=bonus_affordable_req,
        waive_planning_fees=waive_planning,
        waive_building_permit=waive_building,
        tap_fee_reduction_pct=tap_fee_reduction,
        use_tax_rebate_pct=use_tax_rebate
    )

    # Run calculations
    dev_proforma = DeveloperProForma(project, policy, ami_data)
    dev_results = dev_proforma.calculate()

    community_analysis = CommunityBenefitAnalysis(dev_results, policy)
    community_results = community_analysis.calculate()

    # ========================================================================
    # MAIN DISPLAY: KEY METRICS
    # ========================================================================

    st.header("📊 Scenario Results")

    # Top-line metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Total Units Created",
            f"{dev_results['total_units']}",
            delta=f"+{dev_results['bonus_units']} bonus" if dev_results['bonus_units'] > 0 else None
        )

    with col2:
        st.metric(
            "Affordable Units",
            f"{dev_results['total_affordable']}",
            delta=f"{(dev_results['total_affordable']/dev_results['total_units']*100):.0f}% of total"
        )

    with col3:
        feasible_color = "normal" if dev_results['developer_feasible'] else "inverse"
        st.metric(
            "Developer Net Gain",
            f"${dev_results['net_developer_gain']:,.0f}",
            delta="Feasible" if dev_results['developer_feasible'] else "Not Feasible",
            delta_color=feasible_color
        )

    with col4:
        st.metric(
            "City Cost per Unit-Year",
            f"${community_results['cost_per_unit_year']:,.0f}",
            delta=f"{community_results['unit_years']:.0f} unit-years"
        )

    # ========================================================================
    # TABS FOR DETAILED ANALYSIS
    # ========================================================================

    tab1, tab2, tab3, tab4 = st.tabs([
        "💰 Developer Economics",
        "🏘️ Community Benefit",
        "📈 Comparisons",
        "💾 Export & Share"
    ])

    with tab1:
        st.subheader("Developer Pro Forma")

        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown("### Benefits to Developer")

            benefits_data = {
                'Category': [
                    'Density Bonus Value',
                    'Fee Waivers',
                    '  Building Permits',
                    '  Tap/System Fees',
                    '  Use Tax Rebate',
                    '  Planning Fees',
                    'Fast Track Time Savings',
                    '**TOTAL BENEFITS**'
                ],
                'Amount': [
                    f"${dev_results['density_bonus_value']:,.0f}",
                    f"${dev_results['total_fee_waivers']:,.0f}",
                    f"${dev_results['building_permit_waived']:,.0f}",
                    f"${dev_results['tap_fee_savings']:,.0f}",
                    f"${dev_results['use_tax_savings']:,.0f}",
                    f"${dev_results['planning_fees_waived']:,.0f}",
                    f"${dev_results['time_savings']:,.0f}",
                    f"**${dev_results['total_benefits']:,.0f}**"
                ]
            }
            st.table(pd.DataFrame(benefits_data))

        with col_b:
            st.markdown("### Costs to Developer")

            costs_data = {
                'Category': [
                    'Market Rent (2BR)',
                    'Affordable Rent (2BR)',
                    'Monthly Rent Gap',
                    f'× {dev_results["total_affordable"]} units',
                    f'× {policy.affordability_period_years} years',
                    '**TOTAL LOST RENT**'
                ],
                'Amount': [
                    f"${dev_results['market_rent']:,.0f}",
                    f"${dev_results['affordable_rent']:,.0f}",
                    f"${dev_results['monthly_rent_gap']:,.0f}",
                    '',
                    '',
                    f"**${dev_results['total_lost_rent']:,.0f}**"
                ]
            }
            st.table(pd.DataFrame(costs_data))

        st.markdown("---")

        col_c, col_d, col_e = st.columns(3)

        with col_c:
            st.metric("Net Developer Position", f"${dev_results['net_developer_gain']:,.0f}")

        with col_d:
            st.metric("Total Project Cost", f"${dev_results['total_project_cost']:,.0f}")

        with col_e:
            st.metric("Return on Investment", f"{dev_results['roi_pct']:.2f}%")

        # Waterfall chart
        st.markdown("### Financial Waterfall")

        fig = go.Figure(go.Waterfall(
            orientation="v",
            measure=["relative", "relative", "relative", "relative", "total"],
            x=["Density Bonus", "Fee Waivers", "Time Savings", "Lost Rent", "Net Position"],
            y=[
                dev_results['density_bonus_value'],
                dev_results['total_fee_waivers'],
                dev_results['time_savings'],
                -dev_results['total_lost_rent'],
                dev_results['net_developer_gain']
            ],
            connector={"line": {"color": "rgb(63, 63, 63)"}},
            decreasing={"marker": {"color": "#EF553B"}},
            increasing={"marker": {"color": "#00CC96"}},
            totals={"marker": {"color": "#636EFA"}}
        ))

        fig.update_layout(
            title="Developer Financial Impact",
            showlegend=False,
            height=400
        )

        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader("Community Benefit Analysis")

        col_x, col_y = st.columns(2)

        with col_x:
            st.markdown("### City Investment")

            city_data = {
                'Metric': [
                    'Total City Investment',
                    'Affordable Units Created',
                    'Affordability Period',
                    'Total Unit-Years',
                    '',
                    'Cost per Affordable Unit',
                    'Cost per Unit per Year',
                    'Cost per Unit-Year'
                ],
                'Value': [
                    f"${community_results['city_investment']:,.0f}",
                    f"{community_results['affordable_units']:.0f} units",
                    affordability_display,
                    f"{community_results['unit_years']:.0f}",
                    '',
                    f"${community_results['cost_per_unit_total']:,.0f}",
                    f"${community_results['cost_per_unit_per_year']:,.0f}",
                    f"${community_results['cost_per_unit_year']:,.0f}"
                ]
            }
            st.table(pd.DataFrame(city_data))

        with col_y:
            st.markdown("### Economic Impact")

            jobs_data = {
                'Impact': [
                    'Construction Jobs (temp)',
                    'Permanent Jobs Created',
                    'Total Housing Units',
                    'Estimated Population Served',
                    '',
                    '20-Year Projection',
                    f'  Cycles ({policy.affordability_period_years} yr terms)',
                    '  Total 20-Year Cost'
                ],
                'Value': [
                    f"{community_results['construction_jobs']:.0f} jobs",
                    f"{community_results['permanent_jobs']:.0f} jobs",
                    f"{dev_results['total_units']} units",
                    f"{dev_results['total_units'] * 2.3:.0f} people",
                    '',
                    '',
                    f"{community_results['cycles_in_20_years']:.1f} cycles",
                    f"${community_results['cost_20_year']:,.0f}"
                ]
            }
            st.table(pd.DataFrame(jobs_data))

        # Units breakdown pie chart
        st.markdown("### Unit Mix")

        fig_units = go.Figure(data=[go.Pie(
            labels=['Affordable Units', 'Market Rate Units'],
            values=[dev_results['total_affordable'], dev_results['market_rate_units']],
            hole=.3,
            marker_colors=['#00CC96', '#AB63FA']
        )])

        fig_units.update_layout(
            title=f"Total Units: {dev_results['total_units']}",
            height=350
        )

        st.plotly_chart(fig_units, use_container_width=True)

    with tab3:
        st.subheader("Scenario Comparisons")

        st.markdown("""
        Compare this scenario against alternative policy choices. Select comparison scenarios below.
        """)

        # Quick comparison scenarios
        col_comp1, col_comp2 = st.columns(2)

        with col_comp1:
            st.markdown("#### Alternative Affordability Periods")

            comparison_periods = [5, 15, 20, 30, 50]
            comparison_data = []

            for years in comparison_periods:
                temp_policy = PolicySettings(
                    affordability_period_years=years,
                    rental_ami_threshold=rental_ami,
                    ownership_ami_threshold=ownership_ami,
                    min_affordable_pct=min_affordable_pct,
                    density_bonus_pct=density_bonus_pct,
                    bonus_affordable_req=bonus_affordable_req,
                    waive_planning_fees=waive_planning,
                    waive_building_permit=waive_building,
                    tap_fee_reduction_pct=tap_fee_reduction,
                    use_tax_rebate_pct=use_tax_rebate
                )

                temp_dev = DeveloperProForma(project, temp_policy, ami_data)
                temp_results = temp_dev.calculate()
                temp_comm = CommunityBenefitAnalysis(temp_results, temp_policy)
                temp_comm_results = temp_comm.calculate()

                comparison_data.append({
                    'Period': f"{years} yrs" if years < 99 else "Permanent",
                    'Developer Net': temp_results['net_developer_gain'],
                    'Cost/Unit-Yr': temp_comm_results['cost_per_unit_year'],
                    '20-Yr Cost': temp_comm_results['cost_20_year']
                })

            df_comp = pd.DataFrame(comparison_data)

            # Format currency
            df_comp['Developer Net'] = df_comp['Developer Net'].apply(lambda x: f"${x:,.0f}")
            df_comp['Cost/Unit-Yr'] = df_comp['Cost/Unit-Yr'].apply(lambda x: f"${x:,.0f}")
            df_comp['20-Yr Cost'] = df_comp['20-Yr Cost'].apply(lambda x: f"${x:,.0f}")

            st.dataframe(df_comp, use_container_width=True, hide_index=True)

        with col_comp2:
            st.markdown("#### Alternative AMI Thresholds")

            ami_scenarios = [
                ("60% AMI", 0.60),
                ("80% AMI", 0.80)
            ]

            ami_comparison = []

            for name, ami_pct in ami_scenarios:
                temp_policy = PolicySettings(
                    affordability_period_years=affordability_period,
                    rental_ami_threshold=ami_pct,
                    ownership_ami_threshold=ownership_ami,
                    min_affordable_pct=min_affordable_pct,
                    density_bonus_pct=density_bonus_pct,
                    bonus_affordable_req=bonus_affordable_req,
                    waive_planning_fees=waive_planning,
                    waive_building_permit=waive_building,
                    tap_fee_reduction_pct=tap_fee_reduction,
                    use_tax_rebate_pct=use_tax_rebate
                )

                temp_dev = DeveloperProForma(project, temp_policy, ami_data)
                temp_results = temp_dev.calculate()

                ami_comparison.append({
                    'AMI Level': name,
                    'Affordable Rent': f"${temp_results['affordable_rent']:,.0f}",
                    'Rent Gap': f"${temp_results['monthly_rent_gap']:,.0f}",
                    'Developer Net': f"${temp_results['net_developer_gain']:,.0f}"
                })

            st.dataframe(pd.DataFrame(ami_comparison), use_container_width=True, hide_index=True)

        # Scatter plot: Cost vs Affordability
        st.markdown("#### Tradeoff Analysis: City Cost vs. Affordability Duration")

        scatter_data = []
        for years in [5, 10, 15, 20, 30, 50]:
            temp_policy = PolicySettings(
                affordability_period_years=years,
                rental_ami_threshold=rental_ami,
                ownership_ami_threshold=ownership_ami,
                min_affordable_pct=min_affordable_pct,
                density_bonus_pct=density_bonus_pct,
                bonus_affordable_req=bonus_affordable_req,
                waive_planning_fees=waive_planning,
                waive_building_permit=waive_building,
                tap_fee_reduction_pct=tap_fee_reduction,
                use_tax_rebate_pct=use_tax_rebate
            )

            temp_dev = DeveloperProForma(project, temp_policy, ami_data)
            temp_results = temp_dev.calculate()
            temp_comm = CommunityBenefitAnalysis(temp_results, temp_policy)
            temp_comm_results = temp_comm.calculate()

            scatter_data.append({
                'Years': years,
                'Cost per Unit-Year': temp_comm_results['cost_per_unit_year'],
                'Developer Net': temp_results['net_developer_gain'],
                'Feasible': 'Yes' if temp_results['developer_feasible'] else 'No'
            })

        df_scatter = pd.DataFrame(scatter_data)

        fig_scatter = px.scatter(
            df_scatter,
            x='Years',
            y='Cost per Unit-Year',
            size='Developer Net',
            color='Feasible',
            color_discrete_map={'Yes': '#00CC96', 'No': '#EF553B'},
            title="City Cost Efficiency vs. Affordability Duration",
            labels={'Years': 'Affordability Period (Years)',
                   'Cost per Unit-Year': 'City Cost per Unit-Year ($)'}
        )

        # Add current scenario marker
        fig_scatter.add_trace(go.Scatter(
            x=[affordability_period],
            y=[community_results['cost_per_unit_year']],
            mode='markers',
            marker=dict(size=20, color='yellow', symbol='star', line=dict(width=2, color='black')),
            name='Current Scenario',
            showlegend=True
        ))

        st.plotly_chart(fig_scatter, use_container_width=True)

    with tab4:
        st.subheader("Export & Share Results")

        st.markdown("""
        Download this scenario's results or share a link to recreate these settings.
        """)

        # Summary for export
        summary = {
            'Policy Settings': {
                'Affordability Period': affordability_display,
                'Rental AMI Threshold': f"{int(rental_ami*100)}%",
                'Ownership AMI Threshold': f"{int(ownership_ami*100)}%",
                'Minimum Affordable %': f"{int(min_affordable_pct*100)}%",
                'Density Bonus %': f"{int(density_bonus_pct*100)}%",
                'Bonus Units Affordable %': f"{int(bonus_affordable_req*100)}%",
                'Tap Fee Reduction': f"{int(tap_fee_reduction*100)}%",
                'Use Tax Rebate': f"{int(use_tax_rebate*100)}%"
            },
            'Developer Results': {
                'Total Units': dev_results['total_units'],
                'Affordable Units': dev_results['total_affordable'],
                'Total Benefits': f"${dev_results['total_benefits']:,.0f}",
                'Total Lost Rent': f"${dev_results['total_lost_rent']:,.0f}",
                'Net Position': f"${dev_results['net_developer_gain']:,.0f}",
                'Feasible?': 'Yes' if dev_results['developer_feasible'] else 'No'
            },
            'Community Results': {
                'City Investment': f"${community_results['city_investment']:,.0f}",
                'Affordable Units': community_results['affordable_units'],
                'Unit-Years': community_results['unit_years'],
                'Cost per Unit-Year': f"${community_results['cost_per_unit_year']:,.0f}",
                '20-Year Cost': f"${community_results['cost_20_year']:,.0f}"
            }
        }

        # Convert to DataFrame for display
        summary_dfs = []
        for section, data in summary.items():
            df = pd.DataFrame(list(data.items()), columns=['Metric', 'Value'])
            summary_dfs.append((section, df))

        for section_name, df in summary_dfs:
            st.markdown(f"**{section_name}**")
            st.dataframe(df, use_container_width=True, hide_index=True)

        # Download button
        # Create CSV export
        export_data = []
        for section, data in summary.items():
            for key, value in data.items():
                export_data.append({'Section': section, 'Metric': key, 'Value': value})

        export_df = pd.DataFrame(export_data)
        csv = export_df.to_csv(index=False)

        st.download_button(
            label="📥 Download Results (CSV)",
            data=csv,
            file_name=f"delta_fast_track_scenario_{affordability_period}yr.csv",
            mime="text/csv"
        )

        st.markdown("---")

        st.markdown("""
        ### About This Tool

        This simulator models the financial tradeoffs of the City of Delta Fast Track Program
        for affordable housing development under Prop 123.

        **Data Sources:**
        - 2025 Delta County AMI data (HUD)
        - City of Delta 2025 Fee Schedule
        - City of Delta Housing Needs Assessment (2023)
        - RPI Incentive Policy Assessment (Feb 2025)

        **Calculations:**
        - Developer benefits include density bonus value, fee waivers, and time savings
        - Developer costs include lost rental income over the affordability period
        - Community costs represent forgone revenue and incentives
        - Cost per unit-year normalizes across different affordability periods

        Built for the City of Delta Focus Group - November 2025
        """)


if __name__ == "__main__":
    main()
