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
    construction_cost_per_unit: float = 200000  # Based on non-Denver CO avg ($237K total - land)
    land_dev_value_per_unit: float = 35000  # Delta County avg ~$6,795/acre, ~5 units/acre

    # Market rents by bedroom size (Delta, CO - from Grand Mesa Flats market data)
    market_rent_1br: float = 1211  # 85% of 2BR (estimated)
    market_rent_2br: float = 1425  # Confirmed from Grand Mesa Flats
    market_rent_3br: float = 1710  # 120% of 2BR (estimated)

    # Typical unit mix for multi-family development
    unit_mix: dict = None  # Will default to {'1BR': 0.20, '2BR': 0.60, '3BR': 0.20}

    market_sale_price: float = 334000  # Median home price in Delta
    construction_valuation: float = 9600000  # For fee calculations

    def __post_init__(self):
        """Set default unit mix if not provided"""
        if self.unit_mix is None:
            self.unit_mix = {'1BR': 0.20, '2BR': 0.60, '3BR': 0.20}

    def get_weighted_market_rent(self) -> float:
        """Calculate weighted average market rent across bedroom types"""
        market_rents = {
            '1BR': self.market_rent_1br,
            '2BR': self.market_rent_2br,
            '3BR': self.market_rent_3br
        }
        return sum(market_rents[br] * self.unit_mix[br] for br in self.unit_mix if br in market_rents)

@dataclass
class PolicySettings:
    """Fast Track policy levers"""
    # Affordability requirements
    affordability_period_years: int = 30
    rental_ami_threshold: float = 0.80  # 60% or 80%
    ownership_ami_threshold: float = 1.00  # 100%, 110%, or 120%
    min_affordable_pct: float = 0.25  # 25% of original units
    ownership_pct: float = 0.0  # % of affordable units that are ownership (0-1)

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
    """2025 Delta County AMI data from CHFA"""
    # 2025 Income Limits (2 Person Household)
    ami_60_2person: float = 48960
    ami_70_2person: float = 57120
    ami_80_2person: float = 65280
    ami_90_2person: float = 73440
    ami_100_2person: float = 81600
    ami_110_2person: float = 89760
    ami_120_2person: float = 97920

    # CHFA Maximum Rents by Bedroom Size
    # Source: 2025 Delta County CHFA Maximum Rents
    chfa_rents_by_bedroom = {
        0.60: {'1BR': 1147, '2BR': 1377, '3BR': 1591},
        0.70: {'1BR': 1338, '2BR': 1606, '3BR': 1856},
        0.80: {'1BR': 1530, '2BR': 1836, '3BR': 2122},
        0.90: {'1BR': 1721, '2BR': 2065, '3BR': 2387},
        1.00: {'1BR': 1912, '2BR': 2295, '3BR': 2652},
        1.10: {'1BR': 2103, '2BR': 2524, '3BR': 2917},
        1.20: {'1BR': 2295, '2BR': 2754, '3BR': 3183}
    }

    def get_affordable_rent(self, ami_pct: float) -> float:
        """Get CHFA maximum rent at given AMI percentage (2BR units)
        Source: 2025 Delta County CHFA Maximum Rents

        Note: This returns 2BR rent for display purposes.
        Use get_weighted_affordable_rent() for calculations."""
        if ami_pct in self.chfa_rents_by_bedroom:
            return self.chfa_rents_by_bedroom[ami_pct]['2BR']
        else:
            # Linear interpolation
            return ami_pct * self.chfa_rents_by_bedroom[1.00]['2BR']

    def get_weighted_affordable_rent(self, ami_pct: float, unit_mix: dict) -> float:
        """Calculate weighted average affordable rent across bedroom types

        Args:
            ami_pct: AMI percentage (e.g., 0.60 for 60% AMI)
            unit_mix: Dict with bedroom types as keys and percentages as values
                     e.g., {'1BR': 0.20, '2BR': 0.60, '3BR': 0.20}

        Returns:
            Weighted average CHFA maximum rent
        """
        if ami_pct not in self.chfa_rents_by_bedroom:
            # Linear interpolation if exact AMI not in table
            base_amt = 1.00
            rent_1br = ami_pct * self.chfa_rents_by_bedroom[base_amt]['1BR']
            rent_2br = ami_pct * self.chfa_rents_by_bedroom[base_amt]['2BR']
            rent_3br = ami_pct * self.chfa_rents_by_bedroom[base_amt]['3BR']
            rents = {'1BR': rent_1br, '2BR': rent_2br, '3BR': rent_3br}
        else:
            rents = self.chfa_rents_by_bedroom[ami_pct]

        # Calculate weighted average
        weighted_rent = sum(rents[br] * unit_mix[br] for br in unit_mix if br in rents)
        return weighted_rent

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
    def building_permit_fee(valuation: float) -> tuple:
        """Calculate building permit fee from Table 3B

        Returns: (total_fee, breakdown_string)
        """
        # From Section 3: Building Permits - Table 3B - 2025 Fee Schedule
        if valuation <= 500:
            fee = 23.50
            breakdown = f"Base fee: ${fee:,.2f}"
        elif valuation <= 2000:
            fee = 23.50 + ((valuation - 500) / 100) * 3.05
            breakdown = f"$23.50 base + ${((valuation - 500) / 100) * 3.05:,.2f} ($3.05 per $100)"
        elif valuation <= 25000:
            fee = 69.25 + ((valuation - 2000) / 1000) * 14.00
            breakdown = f"$69.25 base + ${((valuation - 2000) / 1000) * 14.00:,.2f} ($14 per $1,000)"
        elif valuation <= 50000:
            fee = 391.25 + ((valuation - 25000) / 1000) * 10.10
            breakdown = f"$391.25 base + ${((valuation - 25000) / 1000) * 10.10:,.2f} ($10.10 per $1,000)"
        elif valuation <= 100000:
            fee = 643.75 + ((valuation - 50000) / 1000) * 7.00
            breakdown = f"$643.75 base + ${((valuation - 50000) / 1000) * 7.00:,.2f} ($7 per $1,000)"
        elif valuation <= 500000:
            fee = 993.75 + ((valuation - 100000) / 1000) * 5.60
            breakdown = f"$993.75 base + ${((valuation - 100000) / 1000) * 5.60:,.2f} ($5.60 per $1,000)"
        elif valuation <= 1000000:
            fee = 3233.75 + ((valuation - 500000) / 1000) * 4.75
            breakdown = f"$3,233.75 base + ${((valuation - 500000) / 1000) * 4.75:,.2f} ($4.75 per $1,000)"
        else:
            fee = 5608.75 + ((valuation - 1000000) / 1000) * 3.15
            breakdown = f"$5,608.75 base + ${((valuation - 1000000) / 1000) * 3.15:,.2f} ($3.15 per $1,000)"

        return fee, breakdown

    @staticmethod
    def tap_and_system_fees(num_units: int, tap_size: str = "4_combo") -> tuple:
        """Calculate water/sewer tap and system improvement fees

        Returns: (total_fee, breakdown_dict)
        """
        # Based on 24-unit apartment example with 4" combo domestic/fire tap
        # From Section 8: Trash Collection and Utility Services - 2025 Fee Schedule
        # Water BSIF: $86,100 base + $1,500 per unit after first
        # Water Tapping Fee: $12,420
        # Sewer BSIF: $154,000 base + $2,600 per unit after first

        if tap_size == "4_combo":
            water_bsif_base = 86100
            water_bsif_per_unit = 1500
            water_tapping_fee = 12420
            sewer_bsif_base = 154000
            sewer_bsif_per_unit = 2600
        else:
            # Default calculation for smaller taps
            water_bsif_base = 3000
            water_bsif_per_unit = 1500
            water_tapping_fee = 1680
            sewer_bsif_base = 5450
            sewer_bsif_per_unit = 2600
            sewer_bsif_per_unit = 2600

        # Calculate water fees
        water_bsif = water_bsif_base + (water_bsif_per_unit * max(0, num_units - 1))
        water_total = water_bsif + water_tapping_fee

        # Calculate sewer fees
        sewer_total = sewer_bsif_base + (sewer_bsif_per_unit * max(0, num_units - 1))

        # Total
        total = water_total + sewer_total

        # Breakdown
        breakdown = {
            'Water BSIF': water_bsif,
            'Water Tapping Fee': water_tapping_fee,
            'Sewer BSIF': sewer_total
        }

        return total, breakdown

    @staticmethod
    def use_tax_rebate(materials_cost: float, rebate_pct: float = 0.0) -> tuple:
        """Calculate 3% use tax rebate on materials

        Returns: (rebate_amount, breakdown_string)
        """
        # From Section 3: Building Permits - Use tax is 3% of cost of materials
        full_use_tax = materials_cost * 0.03
        rebate_amount = full_use_tax * rebate_pct

        breakdown = f"Materials: ${materials_cost:,.0f} × 3% = ${full_use_tax:,.0f} full tax\n"
        breakdown += f"Rebate: {rebate_pct*100:.0f}% of ${full_use_tax:,.0f} = ${rebate_amount:,.0f}"

        return rebate_amount, breakdown

    @staticmethod
    def planning_application_fee(num_units: int) -> tuple:
        """Calculate planning fees for multi-family development

        Returns: (total_fee, breakdown_dict)
        """
        # From Section 6: Land Development - 2025 Fee Schedule
        # Preliminary Plat: $500 + $20/lot (unit)
        # Final Plat: $250

        preliminary_plat = 500 + (num_units * 20)
        final_plat = 250
        total = preliminary_plat + final_plat

        breakdown = {
            'Preliminary Plat': preliminary_plat,
            'Final Plat': final_plat
        }

        return total, breakdown


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

        # Split affordable units into rental vs ownership
        ownership_affordable = int(total_affordable * self.policy.ownership_pct)
        rental_affordable = total_affordable - ownership_affordable

        # DEVELOPER BENEFITS

        # 1. Density bonus value
        density_bonus_value = bonus_units * (
            self.project.construction_cost_per_unit +
            self.project.land_dev_value_per_unit
        )

        # 2. Fee waivers
        planning_fees_waived = 0
        planning_fee_breakdown = {}
        if self.policy.waive_planning_fees:
            planning_fees_waived, planning_fee_breakdown = self.fees.planning_application_fee(total_units)

        building_permit_waived = 0
        building_permit_breakdown = ""
        if self.policy.waive_building_permit:
            building_permit_waived, building_permit_breakdown = self.fees.building_permit_fee(
                self.project.construction_valuation
            )

        tap_fees_full, tap_fee_breakdown = self.fees.tap_and_system_fees(total_units)
        tap_fees_reduced = tap_fees_full * (1 - self.policy.tap_fee_reduction_pct)
        tap_fee_savings = tap_fees_full - tap_fees_reduced

        # Materials cost estimate (60% of construction valuation)
        materials_cost = self.project.construction_valuation * 0.60
        use_tax_savings, use_tax_breakdown = self.fees.use_tax_rebate(materials_cost, self.policy.use_tax_rebate_pct)

        # Park fees (only for PUDs, set to 0 for apartments)
        park_fees_waived = 0

        total_fee_waivers = (planning_fees_waived + building_permit_waived +
                            tap_fee_savings + use_tax_savings + park_fees_waived)

        # 3. Time savings
        time_savings = self.policy.fast_track_time_value

        total_benefits = density_bonus_value + total_fee_waivers + time_savings

        # DEVELOPER COSTS

        # 1. Rental income impact from affordable units (over affordability period)
        # NOTE: Model assumes developer retains ownership and manages rental units
        # Use weighted average across bedroom types for more accurate calculation
        market_rent_weighted = self.project.get_weighted_market_rent()
        affordable_rent_weighted = self.ami.get_weighted_affordable_rent(
            self.policy.rental_ami_threshold,
            self.project.unit_mix
        )

        # Calculate rent gap: positive = developer loses money, negative = developer gains rental income
        # When CHFA rents exceed market (70%+ AMI), this becomes negative (a benefit to developer)
        monthly_rent_gap = market_rent_weighted - affordable_rent_weighted

        # Total rental impact over affordability period
        # If gap is negative (CHFA > market), this represents ADDITIONAL rental income above market
        total_lost_rent = (monthly_rent_gap * rental_affordable * 12 *
                          self.policy.affordability_period_years)

        # For display purposes, also calculate 2BR-only values
        market_rent = self.project.market_rent_2br
        affordable_rent = self.ami.get_affordable_rent(self.policy.rental_ami_threshold)

        # 2. Lost profit from ownership affordable units (one-time at sale)
        market_sale_price = self.project.market_sale_price
        affordable_sale_price = self.ami.get_affordable_purchase_price(self.policy.ownership_ami_threshold)
        per_unit_sale_gap = max(0, market_sale_price - affordable_sale_price)

        total_lost_sale_profit = per_unit_sale_gap * ownership_affordable

        # Total developer costs
        total_developer_costs = total_lost_rent + total_lost_sale_profit

        # Net developer position
        net_developer_gain = total_benefits - total_developer_costs

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
            'rental_affordable': rental_affordable,
            'ownership_affordable': ownership_affordable,
            'market_rate_units': market_rate_units,

            # Financial - Benefits
            'density_bonus_value': density_bonus_value,
            'planning_fees_waived': planning_fees_waived,
            'planning_fee_breakdown': planning_fee_breakdown,
            'building_permit_waived': building_permit_waived,
            'building_permit_breakdown': building_permit_breakdown,
            'tap_fee_savings': tap_fee_savings,
            'tap_fee_breakdown': tap_fee_breakdown,
            'use_tax_savings': use_tax_savings,
            'use_tax_breakdown': use_tax_breakdown,
            'park_fees_waived': park_fees_waived,
            'total_fee_waivers': total_fee_waivers,
            'time_savings': time_savings,
            'total_benefits': total_benefits,

            # Financial - Costs (Rental)
            'market_rent': market_rent,  # 2BR only, for display
            'affordable_rent': affordable_rent,  # 2BR only, for display
            'market_rent_weighted': market_rent_weighted,  # Weighted average used in calculation
            'affordable_rent_weighted': affordable_rent_weighted,  # Weighted average used in calculation
            'monthly_rent_gap': monthly_rent_gap,  # Weighted average gap
            'total_lost_rent': total_lost_rent,

            # Financial - Costs (Ownership)
            'market_sale_price': market_sale_price,
            'affordable_sale_price': affordable_sale_price,
            'per_unit_sale_gap': per_unit_sale_gap,
            'total_lost_sale_profit': total_lost_sale_profit,

            # Bottom line
            'total_developer_costs': total_developer_costs,
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

        # City's investment - ONLY actual dollars spent (fee waivers)
        # Does NOT include density bonus value (no money changes hands) or time savings (developer benefit)
        city_investment = self.dev['total_fee_waivers']

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
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Custom CSS for better aesthetics
    st.markdown("""
        <style>
        /* Main container styling */
        .main {
            background-color: #f8f9fa;
        }

        /* Header styling */
        h1 {
            color: #2c3e50;
            font-weight: 600;
            padding-bottom: 10px;
            border-bottom: 3px solid #3498db;
            margin-bottom: 20px;
        }

        h2 {
            color: #34495e;
            font-weight: 500;
            margin-top: 25px;
        }

        h3 {
            color: #7f8c8d;
            font-weight: 500;
        }

        /* Metric cards */
        [data-testid="stMetricValue"] {
            font-size: 28px;
            font-weight: 600;
        }

        [data-testid="stMetricLabel"] {
            font-size: 14px;
            font-weight: 500;
            color: #7f8c8d;
        }

        /* Sidebar styling */
        [data-testid="stSidebar"] {
            background-color: #2c3e50;
        }

        [data-testid="stSidebar"] .stMarkdown {
            color: #ecf0f1;
        }

        [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
            color: #ecf0f1;
        }

        /* Sidebar labels and text - make them visible on dark background */
        [data-testid="stSidebar"] label {
            color: #ecf0f1 !important;
        }

        [data-testid="stSidebar"] p {
            color: #ecf0f1 !important;
        }

        [data-testid="stSidebar"] .stMarkdown p {
            color: #ecf0f1 !important;
        }

        /* Sidebar expander - fix text color and background on dark sidebar */
        [data-testid="stSidebar"] .streamlit-expanderHeader {
            color: #ecf0f1 !important;
            background-color: transparent !important;
        }

        [data-testid="stSidebar"] .streamlit-expanderHeader:hover {
            color: #ecf0f1 !important;
            background-color: rgba(255, 255, 255, 0.1) !important;
        }

        [data-testid="stSidebar"] details summary {
            color: #ecf0f1 !important;
            background-color: transparent !important;
        }

        [data-testid="stSidebar"] details summary:hover {
            color: #ecf0f1 !important;
            background-color: rgba(255, 255, 255, 0.1) !important;
        }

        /* Expander content background */
        [data-testid="stSidebar"] .streamlit-expanderContent {
            background-color: transparent !important;
        }

        [data-testid="stSidebar"] details[open] {
            background-color: transparent !important;
        }

        /* Input fields inside sidebar expander - make them readable */
        [data-testid="stSidebar"] details input[type="number"],
        [data-testid="stSidebar"] details input[type="text"],
        [data-testid="stSidebar"] details select {
            background-color: #ffffff !important;
            color: #2c3e50 !important;
            border: 1px solid rgba(255, 255, 255, 0.3) !important;
        }

        /* Labels inside expander should stay light */
        [data-testid="stSidebar"] details label {
            color: #ecf0f1 !important;
        }

        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
        }

        .stTabs [data-baseweb="tab"] {
            background-color: #ecf0f1;
            border-radius: 4px 4px 0 0;
            padding: 10px 20px;
            font-weight: 500;
        }

        .stTabs [aria-selected="true"] {
            background-color: #3498db;
            color: white;
        }

        /* Tables */
        table {
            width: 100%;
            border-collapse: collapse;
        }

        th {
            background-color: #34495e;
            color: white !important;
            padding: 12px;
            text-align: left;
        }

        thead th {
            color: white !important;
        }

        [data-testid="stTable"] th {
            color: white !important;
        }

        td {
            padding: 10px;
            border-bottom: 1px solid #ecf0f1;
        }

        tr:hover {
            background-color: #f8f9fa;
        }

        /* Info boxes */
        .stAlert {
            border-radius: 8px;
            border-left: 4px solid #3498db;
        }

        /* Buttons */
        .stButton > button {
            background-color: #3498db;
            color: white;
            border-radius: 6px;
            border: none;
            padding: 10px 24px;
            font-weight: 500;
            transition: background-color 0.3s;
        }

        .stButton > button:hover {
            background-color: #2980b9;
        }

        /* Download button */
        .stDownloadButton > button {
            background-color: #27ae60;
            color: white;
            border-radius: 6px;
            border: none;
            padding: 10px 24px;
            font-weight: 500;
        }

        .stDownloadButton > button:hover {
            background-color: #229954;
        }
        </style>
    """, unsafe_allow_html=True)

    st.title("🏘️ City of Delta Fast Track Incentive Simulator")
    st.markdown("""
    <p style='font-size: 18px; color: #7f8c8d; margin-bottom: 30px;'>
    Explore the tradeoffs between affordability period, density bonuses, AMI thresholds,
    and fee waivers. Adjust the policy levers below to see real-time impacts on developer
    feasibility and community benefit.
    </p>
    """, unsafe_allow_html=True)

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
        value=15,
        help="Minimum years units must remain affordable. Current draft: 15 years. Neighbors: 30+ years."
    )
    affordability_display = "Permanent (99+ years)" if affordability_period == 99 else f"{affordability_period} years"

    project_type = st.sidebar.radio(
        "Project Type",
        options=["Rental", "Ownership"],
        index=0,
        help="Choose whether this is a rental or for-sale (ownership) development"
    )

    # Set ownership_pct based on project type (all or nothing)
    ownership_pct = 1.0 if project_type == "Ownership" else 0.0

    # Fixed minimum affordable requirement (shown in assumptions box at top)
    min_affordable_pct = 0.25  # 25% of base units to qualify for Fast Track

    st.sidebar.subheader("Density Bonus")

    density_bonus_pct = st.sidebar.slider(
        "Density Bonus Percentage",
        min_value=0,
        max_value=50,
        value=20,
        step=5,
        format="%d%%",
        help="Additional units allowed beyond base zoning (key policy lever to explore)"
    ) / 100  # Convert to decimal

    bonus_affordable_req = st.sidebar.slider(
        "% of Bonus Units that Must Be Affordable",
        min_value=0,
        max_value=100,
        value=50,
        step=5,
        format="%d%%",
        help="What percentage of the density bonus units must be affordable?"
    ) / 100  # Convert to decimal

    st.sidebar.subheader("Fee Waivers & Reductions")

    waive_planning = st.sidebar.checkbox("Waive Planning Application Fees", value=True)
    waive_building = st.sidebar.checkbox("Waive Building Permit Fees", value=True)

    tap_fee_reduction = st.sidebar.slider(
        "Tap & System Improvement Fee Reduction",
        min_value=0,
        max_value=100,
        value=60,
        step=5,
        format="%d%%",
        help="Tier by affordability period: 20yr=30%, 30yr=60%, 50yr=100%"
    ) / 100  # Convert to decimal

    use_tax_rebate = st.sidebar.slider(
        "Use Tax Rebate",
        min_value=0,
        max_value=100,
        value=50,
        step=5,
        format="%d%%",
        help="Percentage of 3% materials use tax rebated"
    ) / 100  # Convert back to decimal for calculations

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
            min_value=100000,
            max_value=350000,
            value=200000,
            step=10000,
            format="%d"
        )

        land_value = st.number_input(
            "Land/Development Value per Unit",
            min_value=15000,
            max_value=100000,
            value=35000,
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

        st.markdown("---")
        st.markdown("**AMI Thresholds**")

        rental_ami_pct = st.number_input(
            "Rental AMI Threshold (%)",
            min_value=30,
            max_value=80,
            value=80,
            step=10,
            format="%d",
            help="Area Median Income threshold for rental affordable units"
        )
        rental_ami = rental_ami_pct / 100

        ownership_ami_pct = st.number_input(
            "Ownership AMI Threshold (%)",
            min_value=80,
            max_value=120,
            value=100,
            step=10,
            format="%d",
            help="Area Median Income threshold for ownership affordable units"
        )
        ownership_ami = ownership_ami_pct / 100

    # ========================================================================
    # RUN CALCULATIONS
    # ========================================================================

    project = ProjectParams(
        base_units=base_units,
        construction_cost_per_unit=construction_cost,
        land_dev_value_per_unit=land_value,
        market_rent_2br=market_rent,
        market_sale_price=334000,  # Median home price in Delta (from Fast Track Quick Reference)
        construction_valuation=construction_valuation
    )

    policy = PolicySettings(
        affordability_period_years=affordability_period,
        rental_ami_threshold=rental_ami,
        ownership_ami_threshold=ownership_ami,
        min_affordable_pct=min_affordable_pct,
        ownership_pct=ownership_pct,
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

    # Top-line metrics with color coding
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
            <div style='background-color: #e8f4f8; padding: 20px; border-radius: 10px;
                        border-left: 5px solid #3498db;'>
                <p style='color: #7f8c8d; font-size: 14px; margin: 0; font-weight: 500;'>TOTAL UNITS CREATED</p>
                <p style='color: #2c3e50; font-size: 32px; margin: 5px 0; font-weight: 600;'>{dev_results['total_units']}</p>
                <p style='color: #3498db; font-size: 14px; margin: 0;'>+{dev_results['bonus_units']} bonus units</p>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        affordable_pct = (dev_results['total_affordable']/dev_results['total_units']*100)
        rental_units = dev_results['rental_affordable']
        ownership_units = dev_results['ownership_affordable']
        breakdown = f"{rental_units} rental, {ownership_units} ownership" if ownership_units > 0 else f"{rental_units} rental units"

        st.markdown(f"""
            <div style='background-color: #e8f8f5; padding: 20px; border-radius: 10px;
                        border-left: 5px solid #27ae60;'>
                <p style='color: #7f8c8d; font-size: 14px; margin: 0; font-weight: 500;'>AFFORDABLE UNITS</p>
                <p style='color: #2c3e50; font-size: 32px; margin: 5px 0; font-weight: 600;'>{dev_results['total_affordable']}</p>
                <p style='color: #27ae60; font-size: 14px; margin: 0;'>{breakdown}</p>
            </div>
        """, unsafe_allow_html=True)

    with col3:
        adds_value = dev_results['developer_feasible']
        box_color = "#e8f8f5" if adds_value else "#fee"
        border_color = "#27ae60" if adds_value else "#e74c3c"
        text_color = "#27ae60" if adds_value else "#e74c3c"
        status_text = "✓ Developers Will Participate" if adds_value else "✗ Unlikely to Participate"

        st.markdown(f"""
            <div style='background-color: {box_color}; padding: 20px; border-radius: 10px;
                        border-left: 5px solid {border_color};'>
                <p style='color: #7f8c8d; font-size: 14px; margin: 0; font-weight: 500;'>FAST TRACK VALUE</p>
                <p style='color: #2c3e50; font-size: 32px; margin: 5px 0; font-weight: 600;'>${dev_results['net_developer_gain']:,.0f}</p>
                <p style='color: {text_color}; font-size: 14px; margin: 0; font-weight: 600;'>{status_text}</p>
                <p style='color: #95a5a6; font-size: 12px; margin-top: 8px; font-style: italic;'>Value for {dev_results['total_affordable']} deed-restricted units; {dev_results['market_rate_units']} units remain market-rate</p>
            </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
            <div style='background-color: #fef5e7; padding: 20px; border-radius: 10px;
                        border-left: 5px solid #f39c12;'>
                <p style='color: #7f8c8d; font-size: 14px; margin: 0; font-weight: 500;'>CITY COST PER UNIT-YEAR</p>
                <p style='color: #2c3e50; font-size: 32px; margin: 5px 0; font-weight: 600;'>${community_results['cost_per_unit_year']:,.0f}</p>
                <p style='color: #f39c12; font-size: 14px; margin: 0;'>{community_results['unit_years']:.0f} total unit-years</p>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='margin-top: 30px;'></div>", unsafe_allow_html=True)

    # ========================================================================
    # CAPITAL STACK CONTEXT BOX
    # ========================================================================

    st.info("""
**What This Shows:** This simulator models the **City of Delta's contribution** to affordable housing deals through Fast Track incentives. Actual projects combine multiple funding sources:

- **Prop 123 Compliance** → Unlocks state land banking, concessionary debt, down payment assistance
- **Tax Credits** → LIHTC (4% or 9%), state housing credits
- **Grants** → HOME, CDBG, DOLA, state housing funds
- **Public-Private Partnerships** → Land contribution, housing authority participation, non-profit developers
- **Private Capital** → Construction loans, permanent financing, developer equity

Fast Track Value shows whether the *city's piece* makes the deal more attractive — the full capital stack determines overall feasibility.
    """)

    # ========================================================================
    # COMPREHENSIVE METHODOLOGY & DATA SOURCES
    # ========================================================================

    with st.expander("📖 Methodology & Data Sources"):
        st.markdown("""
        ### Model Assumptions

        **Rental Units:**
        - Developer retains ownership and manages rental units over the entire affordability period
        - Cost = monthly rent gap × rental units × 12 months × affordability years
        - Longer affordability periods = higher developer costs

        **Ownership Units:**
        - Developer sells units at affordable price (one-time discount)
        - Cost = (market price - affordable price) × ownership units
        - Affordability period enforced through deed restrictions/resale controls
        - Developer cost is upfront at sale; period doesn't affect developer's bottom line

        ---

        ### Calculation Methodology

        **Developer Benefits:**
        1. **Density Bonus Value:** Additional units allowed × (construction cost + land value per unit)
           - **Construction cost: \\$200,000/unit** — Based on Grand Junction residential construction
             (\\$120-180/sq ft × ~900 sq ft avg unit = \\$108K-162K) plus 25% for multifamily complexity
           - **Land/development value: \\$35,000/unit** — Delta County undeveloped land averages
             \\$6,795/acre; at ~5 units/acre = ~\\$35K/unit including site development
           - **Total: \\$235,000/unit** — Validated against Black Canyon Flats (Montrose, 2024):
             \\$22M ÷ 60 units = \\$367K total development cost; our figure represents hard costs only
        2. **Fee Waivers:** Building permits + tap/sewer fees + use tax rebate + planning fees
           - Based on City of Delta 2025 Fee Schedule
        3. **Fast Track Time Savings:** \\$50,000 in reduced carrying costs

        **Developer Costs:**
        1. **Rental Units:** Weighted average rent gap × rental units × 12 months × affordability years
           - **Unit Mix Assumption:** 20% 1BR, 60% 2BR, 20% 3BR (typical multi-family)
           - **Market Rents:** 1BR \\$1,211, 2BR \\$1,425, 3BR \\$1,710
           - **Weighted Avg Market Rent:** \\$1,439/mo
           - **CHFA Rents:** Weighted average at selected AMI level
           - **Key Insight:** At 70% AMI and above, CHFA rents exceed market - NO rental cost!
        2. **Ownership Units:** Gap between market sale price (\\$334,000 median) and affordable sale price (based on AMI)

        ---

        ### Fee Calculations (City of Delta 2025 Fee Schedule)

        **Building Permit Fees (Section 3, Table 3B):**
        - Tiered formula based on construction valuation
        - For example project (\\$9.6M): ~\\$32,699

        **Planning Fees (Section 6, Land Development):**
        - Preliminary Plat: \\$500 + (\\$20 × number of units)
        - Final Plat: \\$250
        - For example project (24 units): \\$1,230

        **Tap & System Improvement Fees (Section 8, Tables 8B & 8C):**
        - Water BSIF: \\$86,100 base + \\$1,500 per additional unit
        - Water Tapping Fee: \\$12,420 (4" combo meter)
        - Sewer BSIF: \\$154,000 base + \\$2,600 per additional unit
        - For example project (24 units): \\$346,820 total

        **Use Tax (Section 3D):**
        - 3% of materials cost (materials ≈ 60% of construction valuation)
        - Rebate: 0% to 100% based on policy slider
        - For example project (\\$9.6M valuation): \\$172,800 tax, rebate varies by policy

        ---

        ### Data Sources

        - **Rental Limits:** 2025 CHFA Maximum Rents for Delta County (1BR, 2BR, 3BR)
        - **Income Limits:** 2025 HUD Area Median Income for Delta County
        - **Fee Schedule:** City of Delta 2025 Fee Schedule (official)
        - **Market Data:** Grand Mesa Flats rental data (Nov 2025), \\$334,000 median sale price
          - 2BR market rent confirmed: \\$1,425/mo
          - 1BR and 3BR estimated using standard ratios (85% and 120% of 2BR)
        - **Construction Costs:**
          - Grand Junction: \\$120-180/sq ft (HomeBlue, 2024)
          - Black Canyon Flats, Montrose: \\$22M for 60 units = \\$367K total dev cost (2024)
          - Model uses \\$200K/unit (hard costs only, excludes soft costs/financing)
        - **Land Costs:** Delta County avg \\$6,795/acre undeveloped (LandSearch, 2024)
        - **Unit Mix:** Typical multi-family development pattern (20/60/20 split)
        - **Workforce Metrics:**
          - Subsidized workers housed: 1.5 workers per affordable household (conservative estimate)
          - Population served: 2.3 persons per household (Delta County average)
          - Construction jobs: 0.5 jobs per unit (temporary, during construction)

        ---

        ### Important Context

        **This analysis shows Fast Track incentive value compared to affordability costs.**

        Actual project feasibility will depend on a full **capital stack** that typically includes:
        - Low Income Housing Tax Credits (LIHTC)
        - Grant funding (HOME, CDBG, state housing funds)
        - Land contribution or discount
        - Partnership equity (non-profit, housing authority, etc.)
        - Debt financing (construction loans, permanent financing)
        - Developer equity

        The "Fast Track Adds Value" indicator shows whether these incentives help close the financing gap,
        not whether the full project pencils out.
        """)

    # ========================================================================
    # TABS FOR DETAILED ANALYSIS
    # ========================================================================

    tab_instructions, tab1, tab2, tab3 = st.tabs([
        "📋 Instructions",
        "📊 Results",
        "📈 Comparisons",
        "💾 Export"
    ])

    with tab_instructions:
        st.subheader("How to Use This Simulator")

        # Printable HTML content
        printable_html = """
<!DOCTYPE html>
<html>
<head>
    <title>Fast Track Simulator - Instructions</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; line-height: 1.6; }
        h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
        h2 { color: #34495e; margin-top: 30px; }
        h3 { color: #7f8c8d; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th { background-color: #34495e; color: white; padding: 12px; text-align: left; }
        td { padding: 10px; border-bottom: 1px solid #ecf0f1; }
        .info-box { background-color: #e8f4f8; border-left: 4px solid #3498db; padding: 15px; margin: 20px 0; }
        .footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #ecf0f1; color: #7f8c8d; font-size: 14px; }
    </style>
</head>
<body>
    <h1>Fast Track Incentive Simulator</h1>
    <h2>Instructions for Focus Group</h2>

    <h3>Current Draft Settings</h3>
    <table>
        <tr><th>Setting</th><th>Value</th><th>What It Means</th></tr>
        <tr><td><strong>Rental AMI Threshold</strong></td><td>80%</td><td>Households earning up to $65,280/year*</td></tr>
        <tr><td><strong>Ownership AMI Threshold</strong></td><td>100%</td><td>Households earning up to $81,600/year*</td></tr>
        <tr><td><strong>Minimum Affordable Units</strong></td><td>25%</td><td>At least 25% of base units must be affordable</td></tr>
        <tr><td><strong>Default Affordability Period</strong></td><td>15 years</td><td>Units must remain affordable for at least 15 years</td></tr>
    </table>
    <p><em>*2025 HUD Income Limits for Delta County, 2-person household (via CHFA)</em></p>

    <h3>What We Need Your Input On</h3>
    <p><strong>Density Bonus:</strong> How much extra density should we allow? (Currently 20%, range 0-50%)</p>
    <p><strong>Fee Waivers & Reductions:</strong> Tap & System Fee Reduction, Use Tax Rebate, Planning/Building Permits</p>
    <p><strong>Affordability Period:</strong> 15 years vs 30 years — what's the right balance?</p>

    <h3>What to Watch When Changing Inputs</h3>
    <p><strong>Developer Net Gain:</strong> Green = Fast Track adds value. Red = Developer loses money (won't participate!).</p>
    <p><strong>City Cost per Unit-Year:</strong> Lower is better. Longer affordability periods reduce this number.</p>

    <h3>Try This: Finding Your Sweet Spot</h3>
    <ol>
        <li><strong>Note the Starting Point</strong> — Write down Developer Net Gain and City Cost/Unit-Year</li>
        <li><strong>Increase Density Bonus</strong> — Move from 20% to 30%. What changed?</li>
        <li><strong>Try Longer Affordability</strong> — Change to 30 years. Did developer go negative?</li>
        <li><strong>Compensate with Fee Waivers</strong> — Increase Tap Fee Reduction to get back to green</li>
        <li><strong>Compare Rental vs Ownership</strong> — Switch project type and see the difference</li>
        <li><strong>Export Your Scenario</strong> — Download your preferred settings from the Export tab</li>
    </ol>

    <div class="info-box">
        <strong>Key Questions to Consider</strong><br>
        1. What's the minimum density bonus that makes Fast Track attractive?<br>
        2. Can we achieve 30-year affordability without losing developer interest?<br>
        3. Which fee waivers matter most to making projects feasible?<br>
        4. Should rental and ownership projects have different requirements?
    </div>

    <div class="footer">City of Delta Fast Track Focus Group — December 2025</div>
</body>
</html>
        """

        st.download_button(
            label="🖨️ Download Printable Instructions",
            data=printable_html,
            file_name="fast_track_instructions.html",
            mime="text/html"
        )

        st.markdown("""
        ### Current Draft Settings

        These settings reflect the current draft of the Fast Track program:

        | Setting | Value | What It Means |
        |---------|-------|---------------|
        | **Rental AMI Threshold** | 80% | Affordable rental units serve households earning up to \\$65,280/year* |
        | **Ownership AMI Threshold** | 100% | Affordable for-sale homes serve households earning up to \\$81,600/year* |
        | **Minimum Affordable Units** | 25% | To qualify for Fast Track, at least 25% of base units must be affordable |
        | **Default Affordability Period** | 15 years | Units must remain affordable for at least 15 years |

        *\\*2025 HUD Income Limits for Delta County, 2-person household (via CHFA)*
        """)

        st.markdown("---")

        st.markdown("""
        ### What We Need Your Input On

        The Focus Group will help determine the **right balance** for these policy levers:

        **Density Bonus**
        - How much extra density should we allow? (Currently 20%, range 0-50%)
        - What % of bonus units should be affordable? (Currently 50%)

        **Fee Waivers & Reductions**
        - Tap & System Fee Reduction — How much? (Currently 60%)
        - Use Tax Rebate — What percentage? (Currently 50%)
        - Planning/Building Permits — Waive entirely? (Currently yes)

        **Affordability Period Trade-offs**
        - 15 years = Lower developer cost, but less long-term affordability
        - 30 years = More community benefit, but higher developer cost
        """)

        st.markdown("---")

        st.markdown("""
        ### What to Watch When Changing Inputs
        """)

        col_watch1, col_watch2 = st.columns(2)

        with col_watch1:
            st.markdown("""
            **Developer Net Gain**
            - 🟢 Green = Fast Track adds value for builders
            - 🔴 Red = Developer loses money participating

            *If this goes red, developers won't use Fast Track!*
            """)

        with col_watch2:
            st.markdown("""
            **City Cost per Unit-Year**
            - Lower is better (more housing per dollar)
            - Longer affordability periods reduce this

            *The trade-off: More benefits attract developers, but longer periods help community*
            """)

        st.markdown("---")

        st.markdown("""
        ### Try This: Finding Your Sweet Spot

        **Step 1: Note the Starting Point**
        With default settings (15yr, 20% density bonus), note the Developer Net Gain and City Cost/Unit-Year.

        **Step 2: Increase Density Bonus**
        Move the slider from 20% to 30%. What happened to Developer Net Gain? Did affordable units increase?

        **Step 3: Try a Longer Affordability Period**
        Change from 15 years to 30 years. City Cost/Unit-Year should drop, but did Developer Net Gain go negative?

        **Step 4: Compensate with Fee Waivers**
        If developer went negative, try increasing Tap Fee Reduction to 80% or 100%. Can you get back to green?

        **Step 5: Compare Rental vs Ownership**
        Switch "Project Type" to Ownership. How do the economics differ?

        **Step 6: Export Your Scenario**
        Once you find a balanced approach, go to the Export tab and download your results!
        """)

        st.markdown("---")

        st.info("""
        **Key Questions to Consider**

        1. What's the minimum density bonus that makes Fast Track attractive?
        2. Can we achieve 30-year affordability without losing developer interest?
        3. Which fee waivers matter most to making projects feasible?
        4. Should rental and ownership projects have different requirements?
        """)

    with tab1:
        # ================================================================
        # SIMPLE BAR CHART - Benefits vs Costs
        # ================================================================

        # Calculate values for stacked bar
        total_incentives = dev_results['total_benefits']
        fast_track_value = dev_results['net_developer_gain']

        # Determine cost portion based on project type and rent gap
        if project_type == "Ownership":
            cost_label = "Lost Sale Revenue"
            cost_value = dev_results['total_lost_sale_profit']
            has_premium = False
        elif dev_results['monthly_rent_gap'] < 0:
            # CHFA > market: no cost, actually a premium
            cost_label = "Affordability Cost"
            cost_value = 0
            has_premium = True
            premium_value = abs(dev_results['total_lost_rent'])
        elif dev_results['monthly_rent_gap'] == 0:
            cost_label = "Affordability Cost"
            cost_value = 0
            has_premium = False
        else:
            cost_label = "Lost Rental Income"
            cost_value = dev_results['total_lost_rent']
            has_premium = False

        # Create stacked horizontal bar chart
        fig_compare = go.Figure()

        if has_premium:
            # Special case: CHFA > market, show incentives + premium = total value
            fig_compare.add_trace(go.Bar(
                y=['How Fast Track Incentives Break Down'],
                x=[total_incentives],
                orientation='h',
                marker_color='#27ae60',
                text=f"City Incentives: ${total_incentives:,.0f}",
                textposition='inside',
                textfont=dict(color='white', size=14),
                name='City Incentives',
                hovertemplate="City Incentives: $%{x:,.0f}<extra></extra>"
            ))
            fig_compare.add_trace(go.Bar(
                y=['How Fast Track Incentives Break Down'],
                x=[premium_value],
                orientation='h',
                marker_color='#2ecc71',
                text=f"+Rental Premium: ${premium_value:,.0f}",
                textposition='inside',
                textfont=dict(color='white', size=14),
                name='Rental Premium',
                hovertemplate="Rental Premium (CHFA > Market): $%{x:,.0f}<extra></extra>"
            ))
        else:
            # Normal case: incentives split into cost + value
            # Show Fast Track Value first (left side), then cost (right side)
            if fast_track_value >= 0:
                fig_compare.add_trace(go.Bar(
                    y=['How Fast Track Incentives Break Down'],
                    x=[fast_track_value],
                    orientation='h',
                    marker_color='#3498db',
                    text=f"Fast Track Value: ${fast_track_value:,.0f}",
                    textposition='inside',
                    textfont=dict(color='white', size=14),
                    name='Fast Track Value',
                    hovertemplate="Fast Track Value: $%{x:,.0f}<extra></extra>"
                ))

            if cost_value > 0:
                fig_compare.add_trace(go.Bar(
                    y=['How Fast Track Incentives Break Down'],
                    x=[cost_value],
                    orientation='h',
                    marker_color='#e74c3c',
                    text=f"{cost_label}: ${cost_value:,.0f}",
                    textposition='inside',
                    textfont=dict(color='white', size=14),
                    name=cost_label,
                    hovertemplate=f"{cost_label}: $%{{x:,.0f}}<extra></extra>"
                ))

            # If net is negative, show differently
            if fast_track_value < 0:
                fig_compare.add_trace(go.Bar(
                    y=['How Fast Track Incentives Break Down'],
                    x=[total_incentives],
                    orientation='h',
                    marker_color='#27ae60',
                    text=f"City Incentives: ${total_incentives:,.0f}",
                    textposition='inside',
                    textfont=dict(color='white', size=14),
                    name='City Incentives',
                    hovertemplate="City Incentives: $%{x:,.0f}<extra></extra>"
                ))

        fig_compare.update_layout(
            height=100,
            margin=dict(t=10, b=10, l=10, r=40),
            xaxis_title="",
            yaxis_title="",
            showlegend=False,
            xaxis=dict(showgrid=True, gridcolor='rgba(0,0,0,0.1)', showticklabels=False),
            yaxis=dict(tickfont=dict(size=13)),
            barmode='stack',
            bargap=0.3
        )

        st.plotly_chart(fig_compare, use_container_width=True)

        # Caption with key insight
        if dev_results['net_developer_gain'] > 0:
            st.caption(f"✓ Benefits exceed costs by \\${dev_results['net_developer_gain']:,.0f} — Fast Track adds value for developers.")
        else:
            st.caption(f"✗ Costs exceed benefits by \\${abs(dev_results['net_developer_gain']):,.0f} — adjust policy settings to improve feasibility.")

        # Highlight rental income dynamics when CHFA rents exceed market
        if project_type == "Rental" and dev_results['monthly_rent_gap'] < 0:
            rental_premium = abs(dev_results['monthly_rent_gap'])
            ami_pct = int(policy.rental_ami_threshold * 100)
            st.info(f"""
            **Why are Affordability Costs so low?**

            At **{ami_pct}% AMI**, the maximum rent allowed by CHFA (\\${dev_results['affordable_rent_weighted']:,.0f}/mo)
            actually **exceeds** Delta's current market rent (\\${dev_results['market_rent_weighted']:,.0f}/mo) by \\${rental_premium:.0f}/mo.

            This means "affordable" units can charge *more* than market rate — there's no cost to the developer
            from the affordability requirement at this AMI level. The developer keeps all the Fast Track benefits
            (density bonus, fee waivers, time savings) without sacrificing rental income.
            """)
        elif project_type == "Rental" and dev_results['monthly_rent_gap'] == 0:
            ami_pct = int(policy.rental_ami_threshold * 100)
            st.info(f"""
            **Rent Breakeven at {ami_pct}% AMI**

            At this AMI level, CHFA maximum rent equals market rent — no cost or benefit to the developer
            from rental restrictions.
            """)

        st.markdown("---")

        # ================================================================
        # SUMMARY CARDS ROW
        # ================================================================

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Benefits", f"${dev_results['total_benefits']:,.0f}")
        with col2:
            st.metric("Total Costs", f"${dev_results['total_developer_costs']:,.0f}")
        with col3:
            st.metric("City Investment", f"${community_results['city_investment']:,.0f}")
        with col4:
            residents_served = int(round(dev_results['total_units'] * 2.3, -1))  # Round to nearest 10
            st.metric("Residents Served", f"~{residents_served}")

        st.markdown("---")

        # ================================================================
        # COMMUNITY IMPACT SUMMARY
        # ================================================================

        col_left, col_right = st.columns(2)

        with col_left:
            st.markdown("#### City Investment Efficiency")
            efficiency_col1, efficiency_col2, efficiency_col3 = st.columns(3)
            with efficiency_col1:
                st.metric("Cost/Unit-Year", f"${community_results['cost_per_unit_year']:,.0f}")
            with efficiency_col2:
                st.metric("Unit-Years", f"{community_results['unit_years']:.0f}")
            with efficiency_col3:
                st.metric("20-Year Cost", f"${community_results['cost_20_year']:,.0f}")
            st.caption(f"City invests \\${community_results['city_investment']:,.0f} in fee waivers for {community_results['affordable_units']:.0f} affordable units over {affordability_display}.")

        with col_right:
            st.markdown("#### Housing Created")
            housing_col1, housing_col2, housing_col3 = st.columns(3)
            with housing_col1:
                st.metric("Total Units", f"{dev_results['total_units']}")
            with housing_col2:
                st.metric("Affordable", f"{dev_results['total_affordable']}")
            with housing_col3:
                st.metric("Unrestricted", f"{dev_results['market_rate_units']}")
            st.caption(f"{dev_results['total_affordable']} affordable + {dev_results['market_rate_units']} unrestricted = {dev_results['total_units']} total units")

        # ================================================================
        # DETAILED BREAKDOWNS (Expanders)
        # ================================================================

        with st.expander("📋 Detailed Developer Benefits"):
            benefits_detail = {
                'Category': [
                    'Density Bonus Value',
                    '',
                    'Fee Waivers:',
                    '  • Building Permits',
                    '  • Tap/System Fees',
                    '  • Use Tax Rebate',
                    '  • Planning Fees',
                    '',
                    'Fast Track Time Savings',
                    '',
                    'TOTAL BENEFITS'
                ],
                'Amount': [
                    f"${dev_results['density_bonus_value']:,.0f}",
                    '',
                    f"${dev_results['total_fee_waivers']:,.0f}",
                    f"${dev_results['building_permit_waived']:,.0f}",
                    f"${dev_results['tap_fee_savings']:,.0f}",
                    f"${dev_results['use_tax_savings']:,.0f}",
                    f"${dev_results['planning_fees_waived']:,.0f}",
                    '',
                    f"${dev_results['time_savings']:,.0f}",
                    '',
                    f"${dev_results['total_benefits']:,.0f}"
                ]
            }
            st.table(pd.DataFrame(benefits_detail))

        with st.expander("📋 Detailed Developer Costs"):
            costs_detail = {'Category': [], 'Amount': []}

            if dev_results['rental_affordable'] > 0:
                if dev_results['monthly_rent_gap'] >= 0:
                    costs_detail['Category'].extend([
                        'RENTAL UNITS:',
                        f'  Market Rent (weighted avg)',
                        f'  Affordable Rent (weighted avg)',
                        f'  Monthly Gap × {dev_results["rental_affordable"]} units × {policy.affordability_period_years} yrs',
                        ''
                    ])
                    costs_detail['Amount'].extend([
                        '',
                        f"${dev_results['market_rent_weighted']:,.0f}/mo",
                        f"${dev_results['affordable_rent_weighted']:,.0f}/mo",
                        f"${dev_results['total_lost_rent']:,.0f}",
                        ''
                    ])
                else:
                    costs_detail['Category'].extend([
                        'RENTAL UNITS:',
                        f'  Market Rent (weighted avg)',
                        f'  CHFA Rent (weighted avg)',
                        f'  Monthly PREMIUM × {dev_results["rental_affordable"]} units × {policy.affordability_period_years} yrs',
                        ''
                    ])
                    costs_detail['Amount'].extend([
                        '',
                        f"${dev_results['market_rent_weighted']:,.0f}/mo",
                        f"${dev_results['affordable_rent_weighted']:,.0f}/mo",
                        f"-${abs(dev_results['total_lost_rent']):,.0f} (benefit)",
                        ''
                    ])

            if dev_results['ownership_affordable'] > 0:
                costs_detail['Category'].extend([
                    'OWNERSHIP UNITS:',
                    '  Market Sale Price',
                    '  Affordable Sale Price',
                    f'  Gap × {dev_results["ownership_affordable"]} units',
                    ''
                ])
                costs_detail['Amount'].extend([
                    '',
                    f"${dev_results['market_sale_price']:,.0f}",
                    f"${dev_results['affordable_sale_price']:,.0f}",
                    f"${dev_results['total_lost_sale_profit']:,.0f}",
                    ''
                ])

            costs_detail['Category'].append('TOTAL DEVELOPER COSTS')
            costs_detail['Amount'].append(f"${dev_results['total_developer_costs']:,.0f}")

            st.table(pd.DataFrame(costs_detail))

    with tab2:
        st.subheader("Scenario Comparisons")
        st.caption("Compare how different policy choices affect outcomes")

        # ================================================================
        # SCATTER PLOT - Hero visualization at top
        # ================================================================

        scatter_data = []
        for years in [5, 10, 15, 20, 30, 50]:
            temp_policy = PolicySettings(
                affordability_period_years=years,
                rental_ami_threshold=rental_ami,
                ownership_ami_threshold=ownership_ami,
                min_affordable_pct=min_affordable_pct,
                ownership_pct=ownership_pct,
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
                'Developer Net': abs(temp_results['net_developer_gain']),
                'Adds Value': 'Yes' if temp_results['developer_feasible'] else 'No'
            })

        df_scatter = pd.DataFrame(scatter_data)

        fig_scatter = px.scatter(
            df_scatter,
            x='Years',
            y='Cost per Unit-Year',
            size='Developer Net',
            color='Adds Value',
            color_discrete_map={'Yes': '#00CC96', 'No': '#EF553B'},
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

        fig_scatter.update_layout(
            height=350,
            margin=dict(t=20, b=40),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )

        st.plotly_chart(fig_scatter, use_container_width=True)
        st.caption("⭐ Yellow star = your current scenario. Bubble size = developer net gain. Green = Fast Track adds value.")

        st.markdown("---")

        # ================================================================
        # TABBED COMPARISON TABLES
        # ================================================================

        compare_tab1, compare_tab2, compare_tab3 = st.tabs([
            "📅 By Affordability Period",
            "🏠 By Rental AMI",
            "🏡 By Ownership AMI"
        ])

        with compare_tab1:
            comparison_periods = [5, 15, 20, 30, 50]
            comparison_data = []

            for years in comparison_periods:
                temp_policy = PolicySettings(
                    affordability_period_years=years,
                    rental_ami_threshold=rental_ami,
                    ownership_ami_threshold=ownership_ami,
                    min_affordable_pct=min_affordable_pct,
                    ownership_pct=ownership_pct,
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
                    'Period': f"{years} yrs",
                    'Developer Net': temp_results['net_developer_gain'],
                    'Cost/Unit-Yr': temp_comm_results['cost_per_unit_year'],
                    '20-Yr Cost': temp_comm_results['cost_20_year'],
                    'Unit-Years': temp_comm_results['unit_years']
                })

            df_comp = pd.DataFrame(comparison_data)

            # Format currency
            df_comp['Developer Net'] = df_comp['Developer Net'].apply(lambda x: f"${x:,.0f}")
            df_comp['Cost/Unit-Yr'] = df_comp['Cost/Unit-Yr'].apply(lambda x: f"${x:,.0f}")
            df_comp['20-Yr Cost'] = df_comp['20-Yr Cost'].apply(lambda x: f"${x:,.0f}")

            st.dataframe(df_comp, use_container_width=True, hide_index=True)
            st.caption(f"All scenarios use current settings: {int(rental_ami*100)}% rental AMI, {int(density_bonus_pct*100)}% density bonus")

        with compare_tab2:
            rental_ami_scenarios = [
                ("60% AMI", 0.60),
                ("70% AMI", 0.70),
                ("80% AMI", 0.80),
                ("90% AMI", 0.90),
                ("100% AMI", 1.00)
            ]

            rental_ami_comparison = []

            for name, ami_pct in rental_ami_scenarios:
                temp_policy = PolicySettings(
                    affordability_period_years=affordability_period,
                    rental_ami_threshold=ami_pct,
                    ownership_ami_threshold=ownership_ami,
                    min_affordable_pct=min_affordable_pct,
                    ownership_pct=ownership_pct,
                    density_bonus_pct=density_bonus_pct,
                    bonus_affordable_req=bonus_affordable_req,
                    waive_planning_fees=waive_planning,
                    waive_building_permit=waive_building,
                    tap_fee_reduction_pct=tap_fee_reduction,
                    use_tax_rebate_pct=use_tax_rebate
                )

                temp_dev = DeveloperProForma(project, temp_policy, ami_data)
                temp_results = temp_dev.calculate()

                rental_ami_comparison.append({
                    'AMI Level': name,
                    'CHFA Rent': f"${temp_results['affordable_rent_weighted']:,.0f}",
                    'vs Market': f"${temp_results['monthly_rent_gap']:,.0f}",
                    'Developer Net': f"${temp_results['net_developer_gain']:,.0f}"
                })

            st.dataframe(pd.DataFrame(rental_ami_comparison), use_container_width=True, hide_index=True)
            st.caption(f"Market rent: \\${project.get_weighted_market_rent():,.0f}/mo (weighted avg). Negative 'vs Market' = CHFA rent exceeds market.")

        with compare_tab3:
            ownership_ami_scenarios = [
                ("100% AMI", 1.00),
                ("110% AMI", 1.10),
                ("120% AMI", 1.20)
            ]

            ownership_ami_comparison = []

            for name, ami_pct in ownership_ami_scenarios:
                temp_policy = PolicySettings(
                    affordability_period_years=affordability_period,
                    rental_ami_threshold=rental_ami,
                    ownership_ami_threshold=ami_pct,
                    min_affordable_pct=min_affordable_pct,
                    ownership_pct=ownership_pct,
                    density_bonus_pct=density_bonus_pct,
                    bonus_affordable_req=bonus_affordable_req,
                    waive_planning_fees=waive_planning,
                    waive_building_permit=waive_building,
                    tap_fee_reduction_pct=tap_fee_reduction,
                    use_tax_rebate_pct=use_tax_rebate
                )

                temp_dev = DeveloperProForma(project, temp_policy, ami_data)
                temp_results = temp_dev.calculate()

                affordable_sale_price = ami_data.get_affordable_purchase_price(ami_pct)
                sale_gap = project.market_sale_price - affordable_sale_price

                ownership_ami_comparison.append({
                    'AMI Level': name,
                    'Affordable Price': f"${affordable_sale_price:,.0f}",
                    'vs Market': f"${sale_gap:,.0f}",
                    'Developer Net': f"${temp_results['net_developer_gain']:,.0f}"
                })

            st.dataframe(pd.DataFrame(ownership_ami_comparison), use_container_width=True, hide_index=True)
            st.caption(f"Market price: \\${project.market_sale_price:,.0f}. 'vs Market' = developer cost per ownership unit.")

    with tab3:
        st.subheader("Export Results")

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

        # ================================================================
        # EMAIL MY PREFERENCE
        # ================================================================

        st.subheader("Submit Your Preferred Scenario")

        st.markdown("""
        Once you've found settings you'd recommend, click below to email your preference to the Focus Group facilitators.
        """)

        # Build email body
        email_subject = "My Fast Track Preference"
        email_body = f"""My Preferred Fast Track Scenario
================================

POLICY SETTINGS:
- Affordability Period: {affordability_display}
- Project Type: {project_type}
- Density Bonus: {int(density_bonus_pct*100)}%
- Bonus Units Affordable: {int(bonus_affordable_req*100)}%
- Tap Fee Reduction: {int(tap_fee_reduction*100)}%
- Use Tax Rebate: {int(use_tax_rebate*100)}%
- Waive Planning Fees: {'Yes' if waive_planning else 'No'}
- Waive Building Permits: {'Yes' if waive_building else 'No'}

RESULTS (for {base_units}-unit project):
- Total Units: {dev_results['total_units']} ({dev_results['total_affordable']} affordable, {dev_results['market_rate_units']} market-rate)
- Fast Track Value: ${dev_results['net_developer_gain']:,.0f}
- Feasible: {'Yes' if dev_results['developer_feasible'] else 'No'}
- City Cost per Unit-Year: ${community_results['cost_per_unit_year']:,.0f}

WHY I CHOSE THIS:
[Please add your reasoning here]

---
Submitted from Delta Fast Track Simulator
"""

        # URL-encode for mailto link
        import urllib.parse
        encoded_subject = urllib.parse.quote(email_subject)
        encoded_body = urllib.parse.quote(email_body)

        # Create mailto link - replace with your email
        mailto_link = f"mailto:sarah@westernspaces.co?subject={encoded_subject}&body={encoded_body}"

        st.markdown(f"""
        <a href="{mailto_link}" target="_blank" style="
            display: inline-block;
            background-color: #3498db;
            color: white;
            padding: 12px 24px;
            text-decoration: none;
            border-radius: 6px;
            font-weight: 500;
            font-size: 16px;
        ">📧 Email My Preference</a>
        """, unsafe_allow_html=True)

        st.caption("This will open your email client with a pre-filled message. Add your name and reasoning, then send!")

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

        Built for the City of Delta Focus Group - December 2025
        """)


if __name__ == "__main__":
    main()
