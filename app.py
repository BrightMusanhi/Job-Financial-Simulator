import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- PAGE CONFIG ---
st.set_page_config(page_title="Pro Job Comparison Tool", layout="wide")

st.title("⚖️ Job Offer Comparison Tool")
st.markdown("Analyze and compare two different job offers with high-accuracy tax logic.")


# --- TAX LOGIC (2024 IRS Brackets - Single Filer) ---
def calculate_monthly_take_home(gross_annual, state_tax_rate, retirement_rate):
    # 1. 401k Contribution (Pre-tax)
    annual_retirement = gross_annual * (retirement_rate / 100)
    taxable_income = gross_annual - annual_retirement

    # 2. Federal Tax (Progressive Brackets)
    # Brackets: 10% up to 11.6k, 12% to 47.1k, 22% to 100.5k, 24% to 191k
    fed_tax = 0
    if taxable_income > 11600:
        fed_tax += 11600 * 0.10
    else:
        fed_tax += taxable_income * 0.10

    if taxable_income > 47150:
        fed_tax += (47150 - 11600) * 0.12
    elif taxable_income > 11600:
        fed_tax += (taxable_income - 11600) * 0.12

    if taxable_income > 100525:
        fed_tax += (100525 - 47150) * 0.22
    elif taxable_income > 47150:
        fed_tax += (taxable_income - 47150) * 0.22

    if taxable_income > 100525: fed_tax += (taxable_income - 100525) * 0.24

    # 3. FICA (7.65%) & State Tax
    fica_tax = gross_annual * 0.0765
    state_tax = taxable_income * (state_tax_rate / 100)

    total_tax = fed_tax + fica_tax + state_tax
    annual_take_home = taxable_income - total_tax + annual_retirement  # Adding retirement back for wealth tracking

    # Monthly breakdown
    monthly_net_pay = (taxable_income - total_tax) / 12
    return monthly_net_pay, fed_tax, state_tax, fica_tax, annual_retirement


# --- SIDEBAR / INPUTS ---
col_a, col_b = st.columns(2)

with col_a:
    st.header("Offer A")
    salary_a = st.number_input("Annual Salary (A)", 50000, 200000, 85000, step=5000)
    state_a = st.slider("State Tax % (A)", 0.0, 10.0, 5.0)
    rent_a = st.number_input("Monthly Rent (A)", 0, 5000, 1500)
    trans_a = st.number_input("Monthly Transport (A)", 0, 2000, 300)
    other_a = st.number_input("Monthly Living (A)", 0, 3000, 1000)
    ret_a = st.slider("401k Contribution % (A)", 0, 20, 6)

with col_b:
    st.header("Offer B")
    salary_b = st.number_input("Annual Salary (B)", 50000, 200000, 105000, step=5000)
    state_b = st.slider("State Tax % (B)", 0.0, 10.0, 9.0)  # e.g. higher tax for Cali/NY
    rent_b = st.number_input("Monthly Rent (B)", 0, 5000, 2500)
    trans_b = st.number_input("Monthly Transport (B)", 0, 2000, 150)
    other_b = st.number_input("Monthly Living (B)", 0, 3000, 1200)
    ret_b = st.slider("401k Contribution % (B)", 0, 20, 6)

# --- CALCULATIONS ---
pay_a, fed_a, st_a, fica_a, retire_a = calculate_monthly_take_home(salary_a, state_a, ret_a)
pay_b, fed_b, st_b, fica_b, retire_b = calculate_monthly_take_home(salary_b, state_b, ret_b)

surplus_a = pay_a - (rent_a + trans_a + other_a)
surplus_b = pay_b - (rent_b + trans_b + other_b)

wealth_a = (surplus_a * 12) + retire_a
wealth_b = (surplus_b * 12) + retire_b

# --- TOP METRICS ---
st.markdown("---")
m1, m2, m3 = st.columns(3)

# Monthly Surplus Difference
m1.metric("Monthly Surplus (A)", f"${int(surplus_a):,}")
m2.metric("Monthly Surplus (B)", f"${int(surplus_b):,}", delta=f"{int(surplus_b - surplus_a):,}")
m3.metric("Annual Wealth Gap", f"${int(abs(wealth_a - wealth_b)):,}",
          delta=f"{'B is Better' if wealth_b > wealth_a else 'A is Better'}")

# --- VISUALIZATION ---
st.markdown("### Where is your money going?")


def get_pie_data(rent, trans, other, fed, sta, fica, retire, surplus):
    labels = ['Rent', 'Transport', 'Lifestyle', 'Fed Tax', 'State Tax', 'FICA', '401k', 'Savings']
    values = [rent, trans, other, fed / 12, sta / 12, fica / 12, retire / 12, max(0, surplus)]
    # Filter out 0 values for cleaner chart
    filtered = [(l, v) for l, v in zip(labels, values) if v > 0]
    return zip(*filtered)


labels_a, values_a = get_pie_data(rent_a, trans_a, other_a, fed_a, st_a, fica_a, retire_a, surplus_a)
labels_b, values_b = get_pie_data(rent_b, trans_b, other_b, fed_b, st_b, fica_b, retire_b, surplus_b)

fig = make_subplots(rows=1, cols=2, specs=[[{'type': 'domain'}, {'type': 'domain'}]],
                    subplot_titles=['Offer A', 'Offer B'])

fig.add_trace(go.Pie(labels=labels_a, values=values_a, name="A"), 1, 1)
fig.add_trace(go.Pie(labels=labels_b, values=values_b, name="B"), 1, 2)

fig.update_traces(hole=.4, hoverinfo="label+percent+value")
fig.update_layout(height=500)
st.plotly_chart(fig, width='stretch')

# --- DATA TABLE ---
with st.expander("Detailed Comparison Table"):
    comparison_df = pd.DataFrame({
        "Metric (Annual)": ["Gross Salary", "Total Taxes", "401k Invested", "Total Rent", "Total Lifestyle",
                            "Final Liquid Savings", "TOTAL WEALTH GAIN"],
        "Offer A": [salary_a, (fed_a + st_a + fica_a), retire_a, rent_a * 12, other_a * 12, surplus_a * 12, wealth_a],
        "Offer B": [salary_b, (fed_b + st_b + fica_b), retire_b, rent_b * 12, other_b * 12, surplus_b * 12, wealth_b]
    })
    st.table(comparison_df.style.format(subset=["Offer A", "Offer B"], formatter="${:,.0f}"))

# --- ANALYST INSIGHT ---
st.info(
    f"**Data Insight:** Offer {'B' if wealth_b > wealth_a else 'A'} results in a **{abs(wealth_a - wealth_b) / 12:,.0f}** higher monthly net wealth gain, despite differences in cost of living.")