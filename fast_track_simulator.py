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

        /* Ensure all elements inside sidebar expander stay visible */
        [data-testid="stSidebar"] details * {
            color: #ecf0f1 !important;
        }

        [data-testid="stSidebar"] details input,
        [data-testid="stSidebar"] details select {
            background-color: rgba(255, 255, 255, 0.1) !important;
            border: 1px solid rgba(255, 255, 255, 0.2) !important;
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
        value=30,
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
        max_value=30,
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
        max_value=50,
        value=50,
        step=10,
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

        st.markdown("---")
        st.markdown("**AMI Thresholds**")

        rental_ami = st.select_slider(
            "Rental AMI Threshold",
            options=[0.30, 0.40, 0.50, 0.60, 0.70, 0.80],
            value=0.80,
            format_func=lambda x: f"{int(x*100)}% AMI",
            help="Area Median Income threshold for rental affordable units"
        )

        ownership_ami = st.select_slider(
            "Ownership AMI Threshold",
            options=[0.80, 1.00, 1.10, 1.20],
            value=1.00,
            format_func=lambda x: f"{int(x*100)}% AMI",
            help="Area Median Income threshold for ownership affordable units"
        )

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

    # Example project callout with key assumptions
    project_type_display = "Rental" if ownership_pct == 0 else "Ownership"

    st.info(f"""
    **📐 Model Assumptions:**
    - **Base Project Size:** 20 units
    - **Project Type:** {project_type_display}
    - **Rental AMI Threshold:** {int(rental_ami*100)}% AMI
    - **Ownership AMI Threshold:** {int(ownership_ami*100)}% AMI
    - **Minimum Affordable Requirement:** {int(min_affordable_pct*100)}% of base units (to qualify for Fast Track)

    Adjust the policy settings in the sidebar to explore different scenarios and see their impacts.
    """)

    st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)

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
        feasible = dev_results['developer_feasible']
        box_color = "#e8f8f5" if feasible else "#fee"
        border_color = "#27ae60" if feasible else "#e74c3c"
        text_color = "#27ae60" if feasible else "#e74c3c"
        status_text = "✓ Feasible" if feasible else "✗ Not Feasible"

        st.markdown(f"""
            <div style='background-color: {box_color}; padding: 20px; border-radius: 10px;
                        border-left: 5px solid {border_color};'>
                <p style='color: #7f8c8d; font-size: 14px; margin: 0; font-weight: 500;'>DEVELOPER NET GAIN</p>
                <p style='color: #2c3e50; font-size: 32px; margin: 5px 0; font-weight: 600;'>${dev_results['net_developer_gain']:,.0f}</p>
                <p style='color: {text_color}; font-size: 14px; margin: 0; font-weight: 600;'>{status_text}</p>
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

        # How the Numbers Work expander
        with st.expander("ℹ️ How the Numbers Work"):
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

            ### Calculation Methodology

            **Developer Benefits:**
            1. **Density Bonus Value:** Additional units allowed × (construction cost + land value per unit)
               - Construction cost: \\$75,000/unit (conservative estimate)
               - Land/development value: \\$90,000/unit
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

            ### Data Sources
            - **Rental Limits:** 2025 CHFA Maximum Rents for Delta County (1BR, 2BR, 3BR)
            - **Income Limits:** 2025 HUD Area Median Income for Delta County
            - **Fee Schedule:** City of Delta 2025 Fee Schedule (official)
            - **Market Data:** Grand Mesa Flats rental data (Nov 2025), \\$334,000 median sale price
              - 2BR market rent confirmed: \\$1,425/mo
              - 1BR and 3BR estimated using standard ratios (85% and 120% of 2BR)
            - **Construction Costs:** Industry standard estimates for multi-family development
            - **Unit Mix:** Typical multi-family development pattern (20/60/20 split)
            """)

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

            # Show fee calculation breakdowns
            if dev_results['building_permit_waived'] > 0:
                with st.expander("ℹ️ Building Permit Fee Calculation"):
                    st.write(f"**Total: ${dev_results['building_permit_waived']:,.2f}**")
                    st.write(dev_results['building_permit_breakdown'])
                    st.caption("Source: City of Delta 2025 Fee Schedule - Section 3, Table 3B")

            if dev_results['planning_fees_waived'] > 0:
                with st.expander("ℹ️ Planning Fee Calculation"):
                    st.write(f"**Total: ${dev_results['planning_fees_waived']:,.2f}**")
                    for item, amount in dev_results['planning_fee_breakdown'].items():
                        st.write(f"- {item}: ${amount:,.2f}")
                    st.caption("Source: City of Delta 2025 Fee Schedule - Section 6, Land Development")

            if dev_results['tap_fee_savings'] > 0:
                with st.expander("ℹ️ Tap & Sewer Fee Calculation"):
                    st.write(f"**Savings: ${dev_results['tap_fee_savings']:,.2f}** ({policy.tap_fee_reduction_pct*100:.0f}% reduction)")
                    st.write("**Full Fees:**")
                    for item, amount in dev_results['tap_fee_breakdown'].items():
                        st.write(f"- {item}: ${amount:,.2f}")
                    st.caption("Source: City of Delta 2025 Fee Schedule - Section 8, Tables 8B & 8C")

            if dev_results['use_tax_savings'] > 0:
                with st.expander("ℹ️ Use Tax Rebate Calculation"):
                    st.write(f"**Rebate: ${dev_results['use_tax_savings']:,.2f}**")
                    st.write(dev_results['use_tax_breakdown'])
                    st.caption("Source: City of Delta 2025 Fee Schedule - Section 3D")

        with col_b:
            st.markdown("### Costs to Developer")

            costs_data = {
                'Category': [],
                'Amount': []
            }

            # Rental costs (if any)
            if dev_results['rental_affordable'] > 0:
                # Check if this is a cost (positive gap) or benefit (negative gap)
                if dev_results['monthly_rent_gap'] >= 0:
                    # Traditional case: market rent exceeds affordable rent (developer loses money)
                    costs_data['Category'].extend([
                        '**RENTAL UNITS:**',
                        'Market Rent (weighted avg)',
                        'Affordable Rent (weighted avg)',
                        'Monthly Rent Gap',
                        f'× {dev_results["rental_affordable"]} rental units',
                        f'× {policy.affordability_period_years} years',
                        'Subtotal Lost Rent'
                    ])
                    costs_data['Amount'].extend([
                        '',
                        f"${dev_results['market_rent_weighted']:,.0f}",
                        f"${dev_results['affordable_rent_weighted']:,.0f}",
                        f"${dev_results['monthly_rent_gap']:,.0f}",
                        '',
                        '',
                        f"${dev_results['total_lost_rent']:,.0f}"
                    ])
                else:
                    # CHFA rent exceeds market: developer can charge more (benefit, not cost)
                    rental_income_gain = abs(dev_results['total_lost_rent'])
                    costs_data['Category'].extend([
                        '**RENTAL UNITS:**',
                        'Market Rent (weighted avg)',
                        'Affordable Rent (weighted avg)',
                        'Monthly Rent Premium',
                        f'× {dev_results["rental_affordable"]} rental units',
                        f'× {policy.affordability_period_years} years',
                        'Subtotal Extra Rental Income ✓'
                    ])
                    costs_data['Amount'].extend([
                        '',
                        f"${dev_results['market_rent_weighted']:,.0f}",
                        f"${dev_results['affordable_rent_weighted']:,.0f}",
                        f"${abs(dev_results['monthly_rent_gap']):,.0f}",
                        '',
                        '',
                        f"-${rental_income_gain:,.0f}"
                    ])

            # Ownership costs (if any)
            if dev_results['ownership_affordable'] > 0:
                costs_data['Category'].extend([
                    '',
                    '**OWNERSHIP UNITS:**',
                    'Market Sale Price',
                    'Affordable Sale Price',
                    'Per Unit Gap',
                    f'× {dev_results["ownership_affordable"]} ownership units',
                    'Subtotal Lost Profit'
                ])
                costs_data['Amount'].extend([
                    '',
                    '',
                    f"${dev_results['market_sale_price']:,.0f}",
                    f"${dev_results['affordable_sale_price']:,.0f}",
                    f"${dev_results['per_unit_sale_gap']:,.0f}",
                    '',
                    f"${dev_results['total_lost_sale_profit']:,.0f}"
                ])

            # Total
            costs_data['Category'].extend(['', '**TOTAL DEVELOPER COSTS**'])
            costs_data['Amount'].extend(['', f"**${dev_results['total_developer_costs']:,.0f}**"])

            st.table(pd.DataFrame(costs_data))

            # Add info about rental income dynamics
            if dev_results['rental_affordable'] > 0 and dev_results['monthly_rent_gap'] < 0:
                ami_pct = policy.rental_ami_threshold * 100
                rental_premium = abs(dev_results['monthly_rent_gap'])
                st.success(f"""
                **✓ Rental Income Premium at {ami_pct:.0f}% AMI**

                At {ami_pct:.0f}% AMI, the CHFA maximum affordable rent (\\${dev_results['affordable_rent_weighted']:,.0f}/mo weighted avg)
                **exceeds** Delta's current market rent (\\${dev_results['market_rent_weighted']:,.0f}/mo weighted avg) by \\${rental_premium:.0f}/mo.

                **Developer Advantage:** The developer can charge \\${rental_premium:.0f}/mo MORE per affordable unit than market rate,
                generating extra rental income over the {policy.affordability_period_years}-year period.
                This additional income increases developer net gain compared to lower AMI thresholds.
                """)
            elif dev_results['rental_affordable'] > 0 and dev_results['monthly_rent_gap'] == 0:
                ami_pct = policy.rental_ami_threshold * 100
                st.info(f"""
                **At {ami_pct:.0f}% AMI:** CHFA affordable rent equals market rent (\\${dev_results['market_rent_weighted']:,.0f}/mo).
                No cost or benefit to developer from rental restrictions at this AMI level.
                """)
            elif dev_results['rental_affordable'] > 0:
                # Show that weighted average was used
                st.caption(f"💡 Rent gap calculated using weighted average across unit mix: 20% 1BR, 60% 2BR, 20% 3BR. Weighted avg market rent: \\${dev_results['market_rent_weighted']:,.0f}/mo")

        st.markdown("---")

        col_c, col_d, col_e = st.columns(3)

        with col_c:
            st.metric("Net Developer Position", f"${dev_results['net_developer_gain']:,.0f}")

        with col_d:
            st.metric("Total Project Cost", f"${dev_results['total_project_cost']:,.0f}")

        with col_e:
            st.metric("Return on Investment", f"{dev_results['roi_pct']:.2f}%")

        # Stacked bar chart: Benefits vs Costs
        st.markdown("### Developer Financial Impact")

        # Prepare data for stacked bars
        benefits_components = ['Density Bonus', 'Fee Waivers', 'Time Savings']
        benefits_values = [
            dev_results['density_bonus_value'],
            dev_results['total_fee_waivers'],
            dev_results['time_savings']
        ]

        # Check if there's rental income premium to add
        has_rental_premium = (dev_results['rental_affordable'] > 0 and
                             dev_results['total_lost_rent'] < 0)

        # Build cost components dynamically based on what's present
        costs_components = []
        costs_values = []

        # Separate benefits that come from rental income premium
        rental_income_benefit = 0

        if dev_results['rental_affordable'] > 0:
            if dev_results['total_lost_rent'] > 0:
                # Positive = cost to developer
                costs_components.append('Rental Costs')
                costs_values.append(dev_results['total_lost_rent'])
            elif dev_results['total_lost_rent'] < 0:
                # Negative = additional income benefit to developer
                rental_income_benefit = abs(dev_results['total_lost_rent'])

        if dev_results['ownership_affordable'] > 0:
            costs_components.append('Ownership Costs')
            costs_values.append(dev_results['total_lost_sale_profit'])

        # Create stacked bar chart
        fig = go.Figure()

        # Benefits stack (green shades)
        benefit_colors = ['#27ae60', '#2ecc71', '#58d68d', '#7dcea0']

        # Add rental income premium if applicable
        if has_rental_premium:
            benefits_components.append('Rental Income Premium')
            benefits_values.append(rental_income_benefit)

        for i, (component, value) in enumerate(zip(benefits_components, benefits_values)):
            fig.add_trace(go.Bar(
                name=component,
                x=['Benefits'],
                y=[value],
                marker_color=benefit_colors[i % len(benefit_colors)],
                text=f"${value:,.0f}",
                textposition='inside',
                hovertemplate=f'{component}: ${value:,.0f}<extra></extra>'
            ))

        # Costs stack (red shades)
        cost_colors = ['#e74c3c', '#ec7063']
        for i, (component, value) in enumerate(zip(costs_components, costs_values)):
            fig.add_trace(go.Bar(
                name=component,
                x=['Costs'],
                y=[value],
                marker_color=cost_colors[i % len(cost_colors)],
                text=f"${value:,.0f}",
                textposition='inside',
                hovertemplate=f'{component}: ${value:,.0f}<extra></extra>'
            ))

        # Add net position as separate bar
        net_color = '#27ae60' if dev_results['net_developer_gain'] > 0 else '#e74c3c'
        fig.add_trace(go.Bar(
            name='Net Position',
            x=['Net Position'],
            y=[abs(dev_results['net_developer_gain'])],
            marker_color=net_color,
            text=f"${dev_results['net_developer_gain']:,.0f}",
            textposition='outside',
            hovertemplate=f"Net Developer Gain: ${dev_results['net_developer_gain']:,.0f}<extra></extra>"
        ))

        fig.update_layout(
            barmode='stack',
            height=400,
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            yaxis_title="Amount ($)",
            xaxis_title="",
            hovermode='x unified'
        )

        st.plotly_chart(fig, use_container_width=True)

        # Add summary below chart
        total_benefits = sum(benefits_values)
        total_costs = sum(costs_values)
        st.caption(f"**Total Benefits:** \\${total_benefits:,.0f} | **Total Costs:** \\${total_costs:,.0f} | **Net Gain:** \\${dev_results['net_developer_gain']:,.0f}")

    with tab2:
        st.subheader("Community Benefit Analysis")

        # How the Numbers Work expander
        with st.expander("ℹ️ How the Numbers Work"):
            st.markdown("""
            ### Key Metrics Explained

            **Cost per Unit-Year:**
            - Normalizes city investment across different affordability periods
            - Calculation: Total city investment ÷ (affordable units × years)
            - Lower is better = more efficient use of city resources
            - Allows apples-to-apples comparison of different term lengths

            **Total Unit-Years:**
            - Measures total duration of affordability created
            - Calculation: Affordable units × affordability period
            - Example: 7 units for 30 years = 210 unit-years

            **20-Year Total Cost:**
            - Projects long-term budget impact
            - Shows cost to maintain affordable units over 20 years
            - Short terms require re-incentivizing units multiple times
            - Formula: City investment × (20 ÷ affordability period)

            ### Ownership Unit Wealth-Building

            **How Ownership Units Build Wealth:**

            Affordable ownership units help buyers build wealth through home equity. Even with deed restrictions that may cap appreciation, homeowners benefit from:
            - **Monthly payments building equity** instead of paying rent to a landlord
            - **Appreciation within allowed limits** (varies by program and deed restriction terms)
            - **Asset ownership and housing stability** that rental cannot provide
            - **Forced savings** through mortgage principal paydown

            The "developer cost" shown in this tool reflects the one-time discount at initial sale. The buyer's long-term wealth gain depends on:
            - Market appreciation rates
            - Deed restriction terms (resale price caps, shared equity formulas, etc.)
            - Length of homeownership
            - Maintenance and improvements made to the property

            These factors vary significantly and are not calculated in this model. The primary benefit is that buyers are building equity in an asset they own, rather than paying rent.

            ### City Investment Components
            - **Density Bonus Value:** Revenue foregone by allowing more units without charging impact fees
            - **Fee Waivers:** Direct cost to city for waived building permits, tap fees, etc.
            - **Use Tax Rebate:** Sales tax revenue returned to developer on construction materials
            - **Fast Track Time Savings:** Administrative efficiency benefit (no direct city cost)

            ### Workforce Housing Impact
            - **Local Workers Housed:** Estimated workers who can live in Delta due to affordable units
            - Calculation: Affordable units × 1.5 workers per household (average)
            - These are positions already in Delta (teachers, nurses, service workers) who need housing
            - Enables local workforce to live in the community where they work

            ### Data Sources
            - All calculations based on official 2025 City of Delta fee schedules
            - Construction jobs multiplier: 0.5 jobs per unit (temporary, during build)
            - Population estimates use 2.3 persons per household (Delta County average)
            - Workers per household: 1.5 (conservative estimate for working-age affordable housing residents)
            """)

        col_x, col_y = st.columns(2)

        with col_x:
            st.markdown("### City Investment")

            # Show rental vs ownership breakdown
            rental_count = dev_results['rental_affordable']
            ownership_count = dev_results['ownership_affordable']
            unit_breakdown = f"{rental_count} rental, {ownership_count} ownership" if ownership_count > 0 else f"{rental_count} rental"

            city_data = {
                'Metric': [
                    'Affordable Units Created',
                    '  Unit Breakdown',
                    '',
                    'Total City Investment',
                    'Cost per Unit-Year',
                    '20-Year Total Cost',
                    '',
                    'Affordability Period',
                    'Total Unit-Years'
                ],
                'Value': [
                    f"{community_results['affordable_units']:.0f} units",
                    f"{unit_breakdown}",
                    '',
                    f"${community_results['city_investment']:,.0f}",
                    f"${community_results['cost_per_unit_year']:,.0f}",
                    f"${community_results['cost_20_year']:,.0f}",
                    '',
                    affordability_display,
                    f"{community_results['unit_years']:.0f}"
                ]
            }
            st.table(pd.DataFrame(city_data))

            # Add brief explanation for key metric
            st.caption("💡 Cost per Unit-Year normalizes investment across different time periods for fair comparison.")

        with col_y:
            st.markdown("### Workforce Housing Impact")

            # Calculate workforce metrics
            # Assume 1.5 workers per household on average
            workers_housed = dev_results['total_affordable'] * 1.5

            workforce_data = {
                'Impact': [
                    'Total Housing Units',
                    'Affordable Units',
                    'Market Rate Units',
                    '',
                    'Estimated Population Served',
                    'Local Workers Housed',
                    '',
                    'Construction Jobs (temp)'
                ],
                'Value': [
                    f"{dev_results['total_units']} units",
                    f"{dev_results['total_affordable']} units",
                    f"{dev_results['market_rate_units']} units",
                    '',
                    f"{dev_results['total_units'] * 2.3:.0f} people",
                    f"~{workers_housed:.0f} workers",
                    '',
                    f"{community_results['construction_jobs']:.0f} jobs"
                ]
            }
            st.table(pd.DataFrame(workforce_data))

            st.caption("💡 Local workers housed: Affordable units enable teachers, healthcare workers, and service employees to live in Delta.")

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

            # Explanatory note about how period affects costs
            rental_units = int(dev_results['total_affordable'] * (1 - ownership_pct))
            ownership_units = int(dev_results['total_affordable'] * ownership_pct)

            if ownership_pct > 0:
                st.info(f"""
                **How affordability period affects developer costs:**
                - **Rental units ({rental_units}):** Longer period = higher costs (ongoing rent gap × years)
                - **Ownership units ({ownership_units}):** Period doesn't affect developer's upfront cost (one-time sale discount)

                If all units are ownership, developer net gain stays the same across periods.
                """)

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
                    'Period': f"{years} yrs" if years < 99 else "Permanent",
                    'Rental Units': temp_results['rental_affordable'],
                    'Ownership Units': temp_results['ownership_affordable'],
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
            st.markdown("#### Alternative Rental AMI Thresholds")
            st.caption(f"Current ownership AMI: {int(ownership_ami*100)}%")

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
                    'Affordable Rent': f"${temp_results['affordable_rent_weighted']:,.0f}",
                    'Rent Gap': f"${temp_results['monthly_rent_gap']:,.0f}",
                    'Developer Net': f"${temp_results['net_developer_gain']:,.0f}"
                })

            st.dataframe(pd.DataFrame(rental_ami_comparison), use_container_width=True, hide_index=True)

        # Ownership AMI comparison
        st.markdown("#### Alternative Ownership AMI Thresholds")

        col_own1, col_own2 = st.columns(2)

        with col_own1:
            st.caption(f"Current rental AMI: {int(rental_ami*100)}%")

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

                # Calculate affordable sale price based on AMI
                affordable_sale_price = ami_data.get_affordable_purchase_price(ami_pct)
                sale_gap = project.market_sale_price - affordable_sale_price

                ownership_ami_comparison.append({
                    'AMI Level': name,
                    'Affordable Price': f"${affordable_sale_price:,.0f}",
                    'Price Gap': f"${sale_gap:,.0f}",
                    'Developer Net': f"${temp_results['net_developer_gain']:,.0f}"
                })

            st.dataframe(pd.DataFrame(ownership_ami_comparison), use_container_width=True, hide_index=True)

        with col_own2:
            st.info("""
            **Rental vs. Ownership AMI Impact:**

            - **Rental AMI:** Affects monthly rent gap (ongoing cost over affordability period)
            - **Ownership AMI:** Affects one-time sale price discount (upfront cost to developer)

            Higher AMI = less affordable to households, but lower cost to developer.
            """)

        # Scatter plot: Cost vs Affordability
        st.markdown("#### Tradeoff Analysis: City Cost vs. Affordability Duration")

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
                'Developer Net': abs(temp_results['net_developer_gain']),  # Use absolute value for size
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

        Built for the City of Delta Focus Group - December 2025
        """)


if __name__ == "__main__":
    main()
