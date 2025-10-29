import streamlit as st
import pandas as pd
import plotly.express as px
import uuid
from datetime import datetime, timedelta
import random 

# --- 1. Configuration: School Branding, Emission Factors, and Data Schema ---

APP_TITLE = "🌱 HRMS Eco-Score: CarbonCollective – Green Growth for Viksit Bharat 2047"
ORG_NAME = "Hansraj Model School"

# Emission Factors (kg CO₂e per unit) - Adapted for School Activities
EMISSION_FACTORS = {
    "Electricity saved": {"factor": 0.82, "unit": "kWh"},
    "Walk/Bike Commute": {"factor": 0.15, "unit": "km"},
    "Waste recycled": {"factor": 0.90, "unit": "kg"},
    "Trees planted": {"factor": 21.77, "unit": "count"},
    "Solar power used": {"factor": 0.80, "unit": "kWh"},
    "Paper Saved": {"factor": 0.005, "unit": "sheets"},
    "Water Saved": {"factor": 0.0003, "unit": "liters"},
}

USER_ROLES = ["Student", "Faculty/Staff", "Administration", "Eco-Club Lead"]

DATA_COLUMNS = [
    "Entry ID", "Timestamp", "Name", "Role", "Activity", "Quantity", "CO2 Saved (kg)", "Credits"
]

# --- 2. Data Initialization and Mock Data Generation ---

# Set to True to start with a populated dashboard for the demo
GENERATE_MOCK_DATA = True 

def initialize_data():
    """Initializes the main DataFrame in Streamlit's session state."""
    if 'carbon_ledger' not in st.session_state or st.session_state['carbon_ledger'].empty:
        st.session_state['carbon_ledger'] = pd.DataFrame(columns=DATA_COLUMNS)
        if GENERATE_MOCK_DATA:
            st.session_state['carbon_ledger'] = populate_mock_data(st.session_state['carbon_ledger'])

@st.cache_data
def populate_mock_data(df):
    """Adds a large, randomized dummy dataset for a robust demo showcase (80 entries)."""
    
    names_and_roles = [
        ("Aarav Sharma", "Student"), ("Priya Verma", "Faculty/Staff"), 
        ("Mohit Singh", "Student"), ("Ms. Gupta", "Administration"), 
        ("Eco-Club (Group)", "Eco-Club Lead"), ("Neha Jain", "Student"), 
        ("Ravi Kumar", "Faculty/Staff"), ("Zoya Khan", "Student"),
        ("Mr. Das", "Faculty/Staff"), ("Kiran Bedi", "Student"),
        ("Admin Team", "Administration"), ("Student Council", "Eco-Club Lead"),
        ("Alok Vats", "Student"), ("Dr. Meena", "Faculty/Staff"), 
        ("Suresh Reddy", "Student")
    ]
    
    activities = list(EMISSION_FACTORS.keys())
    
    quantity_ranges = {
        "Electricity saved": (1, 15, 'float'),
        "Walk/Bike Commute": (1, 50, 'float'),
        "Waste recycled": (1, 10, 'float'),
        "Trees planted": (1, 5, 'int'),
        "Solar power used": (5, 25, 'float'),
        "Paper Saved": (100, 2000, 'int'),
        "Water Saved": (500, 5000, 'int'),
    }

    mock_entries = []
    NUM_ENTRIES = 80
    start_date = datetime.now() - timedelta(days=60)
    
    for i in range(NUM_ENTRIES):
        name, role = random.choice(names_and_roles)
        activity = random.choice(activities)
        
        min_q, max_q, q_type = quantity_ranges[activity]
        
        if q_type == 'int':
            quantity = random.randint(min_q, max_q)
        else:
            quantity = round(random.uniform(min_q, max_q), 2)
            
        # Distribute entries across the last 60 days
        time_offset = timedelta(days=random.uniform(0, 60), seconds=random.randint(0, 86400))
        timestamp = start_date + time_offset
            
        co2_saved, credits = calculate_credits(activity, quantity)
        
        mock_entries.append({
            "Entry ID": str(uuid.uuid4()),
            "Timestamp": timestamp,
            "Name": name,
            "Role": role,
            "Activity": activity,
            "Quantity": quantity,
            "CO2 Saved (kg)": co2_saved,
            "Credits": credits
        })

    df = pd.DataFrame(mock_entries)
    
    # Sort by timestamp to make the cumulative chart realistic
    return df.sort_values(by="Timestamp").reset_index(drop=True)

def reset_data():
    """Clears the session state ledger and re-initializes."""
    del st.session_state['carbon_ledger']
    initialize_data()
    st.success("Data reset complete. Starting with fresh ledger.")

# --- 3. Core Calculation Logic ---

def calculate_credits(activity, quantity):
    """Calculates CO2 saved and credits for a single activity."""
    if activity in EMISSION_FACTORS and quantity is not None:
        factor = EMISSION_FACTORS[activity]["factor"]
        co2_saved = quantity * factor
        credits = co2_saved  # 1 credit = 1 kg CO2e
        return co2_saved, credits
    return 0.0, 0.0

def add_entry(df, name, role, activity, quantity):
    """Adds a new entry to the DataFrame and applies calculations."""
    co2_saved, credits = calculate_credits(activity, quantity)

    new_row = pd.DataFrame({
        "Entry ID": [str(uuid.uuid4())],
        "Timestamp": [datetime.now()], # Capture real-time log
        "Name": [name],
        "Role": [role],
        "Activity": [activity],
        "Quantity": [quantity],
        "CO2 Saved (kg)": [co2_saved],
        "Credits": [credits]
    })

    return pd.concat([df, new_row], ignore_index=True)

# --- 4. Streamlit UI Components ---

def render_sidebar_form():
    """Renders the data entry form and reset button in the sidebar."""
    st.sidebar.markdown(f"### ✏️ Log Your Green Action")
    
    # Activity selection must be outside the form to trigger a RERUN
    # and update the unit variable dynamically based on user interaction.
    activity = st.sidebar.selectbox("Select Activity", list(EMISSION_FACTORS.keys()), key="activity_select")
    unit = EMISSION_FACTORS[activity]["unit"]
    
    with st.sidebar.form(key="carbon_entry_form"):
        name = st.text_input("Your Full Name", placeholder="e.g., Ananya Deshmukh")
        role = st.selectbox("Your Role / Department", USER_ROLES)
        
        # Quantity input label now correctly uses the dynamically updated 'unit' variable
        quantity = st.number_input(f"Quantity ({unit})", min_value=0.01, step=1.0) 
        
        submitted = st.form_submit_button("✅ Log Contribution")

        if submitted:
            if not name or quantity <= 0:
                st.error("Please ensure your Name is entered and Quantity is greater than zero.")
            else:
                current_df = st.session_state['carbon_ledger']
                st.session_state['carbon_ledger'] = add_entry(current_df, name, role, activity, quantity)
                st.success(f"Contribution logged! {st.session_state['carbon_ledger'].iloc[-1]['Credits']:,.2f} credits added.")
                st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.button("🗑️ Reset All Data", on_click=reset_data)


def render_informative_panel():
    """Renders the panel explaining Carbon Credits and Viksit Bharat alignment."""
    with st.container(border=True):
        st.markdown("### 💡 Understanding Carbon Credits & Viksit Bharat 2047")
        col_c, col_v = st.columns(2)
        
        with col_c:
            st.subheader("What is a Carbon Credit?")
            st.markdown(
                """
                A **Carbon Credit** is a non-monetary unit representing the avoidance or removal of greenhouse gas emissions. 
                In this app, **1 Credit = 1 kg of CO₂e** (Carbon Dioxide Equivalent) saved. 
                When you log a sustainable action (like saving electricity or cycling), 
                you generate credits that contribute to our school's collective goal.
                """
            )
        
        with col_v:
            st.subheader("Alignment with Viksit Bharat 2047")
            st.markdown(
                """
                This initiative directly supports the **Green Growth** and **Digital Empowerment** themes of Viksit Bharat:
                * **Green Growth:** By quantifying individual actions, we drive collective emission reduction.
                * **Digital Empowerment:** We use technology (data-driven tracking) to foster environmental ownership in the community.
                * **Community:** Every student and faculty member becomes an active, informed participant in national sustainability goals.
                """
            )

def render_emission_factors_table():
    """Renders a table showing the carbon credit factor for each activity."""
    st.markdown("---")
    st.subheader("⚖️ Emission Factors and Credit Value (Transparency)")
    
    factor_data = []
    for activity, data in EMISSION_FACTORS.items():
        factor_data.append({
            "Activity": activity,
            "Credits per Unit (kg CO₂e)": data["factor"],
            "Unit": data["unit"]
        })
    
    factor_df = pd.DataFrame(factor_data)
    
    with st.expander("Click to View Carbon Credit Values per Unit"):
        st.dataframe(factor_df, hide_index=True, use_container_width=True)
        st.caption("1 Credit = 1 kg CO₂e Saved.")
        
def render_main_dashboard(df):
    """Renders the main visualization dashboard."""
    if df.empty:
        st.info("No data logged yet. Use the sidebar form to log the first action!")
        return

    # 4.1 Global Metrics
    total_co2_saved = df["CO2 Saved (kg)"].sum()
    total_credits = df["Credits"].sum()
    unique_users = df["Name"].nunique()
    
    st.markdown("### 📊 Organizational Impact Metrics")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(label="Total CO₂ Saved (kg)", value=f"🌍 {total_co2_saved:,.2f} kg", delta="Collective Impact")
    with col2:
        st.metric(label="Total Credits Generated", value=f"⭐ {total_credits:,.2f}", delta="Rewards for Action")
    with col3:
        st.metric(label="Participants", value=f"🧑‍🤝‍🧑 {unique_users}", delta="Unique Contributors")

    # Informative panel
    render_emission_factors_table()

    # 4.2 Top Charts Row (Leaderboard and Pie)
    st.markdown("---")
    col_l, col_p = st.columns([1, 1])

    with col_l:
        st.subheader("🥇 Carbon Leaderboard")
        user_leaderboard = df.groupby("Name")["Credits"].sum().reset_index().sort_values(by="Credits", ascending=False).head(10)
        user_leaderboard["Rank"] = user_leaderboard["Credits"].rank(method="min", ascending=False).astype(int)

        top_contributor = user_leaderboard.iloc[0] if not user_leaderboard.empty else None
        
        if top_contributor is not None:
            st.success(
                f"🏆 Current Green Champion: **{top_contributor['Name']}** "
                f"({top_contributor['Credits']:,.2f} Credits)"
            )

        st.dataframe(user_leaderboard[['Rank', 'Name', 'Credits']], 
                     use_container_width=True, 
                     hide_index=True, 
                     column_config={
                         "Credits": st.column_config.NumberColumn(format="%.2f")
                     })

    with col_p:
        st.subheader("🗂️ Contribution by Role")
        role_contribution = df.groupby("Role")["CO2 Saved (kg)"].sum().reset_index()
        role_contribution.columns = ["Role", "CO2 Saved (kg)"]
        
        fig_pie = px.pie(
            role_contribution,
            values="CO2 Saved (kg)",
            names="Role",
            title="Role-wise Contribution to Total CO₂ Savings",
            hole=.3,
            color_discrete_sequence=px.colors.sequential.Teal
        )
        fig_pie.update_layout(showlegend=False)
        st.plotly_chart(fig_pie, use_container_width=True)


    # 4.3 Activity Charts Row
    st.markdown("---")
    st.subheader("📉 Activity & Role Analysis")
    col_bar, col_drilldown = st.columns(2)
    
    with col_bar:
        # Top 5 Activity Impact (New Visualization)
        st.markdown("#### Top 5 Most Impactful Activities")
        activity_breakdown = df.groupby("Activity")["Credits"].sum().reset_index().sort_values(by="Credits", ascending=False).head(5)
        
        fig_bar = px.bar(
            activity_breakdown,
            x="Credits",
            y="Activity",
            orientation="h",
            color="Activity",
            color_discrete_sequence=px.colors.sequential.Viridis_r
        )
        fig_bar.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_drilldown:
        # Activity Breakdown by Role (New Visualization)
        st.markdown("#### Activity Effectiveness by Role")
        role_activity_breakdown = df.groupby(["Role", "Activity"])["Credits"].sum().reset_index()
        
        fig_drilldown = px.bar(
            role_activity_breakdown,
            x="Role",
            y="Credits",
            color="Activity",
            title="Credits by Role and Activity",
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        st.plotly_chart(fig_drilldown, use_container_width=True)

    # 4.4 Cumulative Timeline
    st.markdown("---")
    st.subheader("📈 Organizational Progress Timeline")
    
    df_timeline = df.copy()
    df_timeline['Date'] = df_timeline['Timestamp'].dt.date
    df_timeline_grouped = df_timeline.groupby('Date')['Credits'].sum().cumsum().reset_index()
    df_timeline_grouped.columns = ['Date', 'Cumulative Credits']

    fig_line = px.line(
        df_timeline_grouped,
        x='Date',
        y='Cumulative Credits',
        markers=True,
        title='Cumulative Carbon Credits Over Time',
        labels={'Date': 'Date', 'Cumulative Credits': 'Total Credits'},
        line_shape='spline',
        color_discrete_sequence=['#4CAF50']
    )
    st.plotly_chart(fig_line, use_container_width=True)


def render_report_export(df):
    """Renders the export functionality and summary message."""
    st.markdown("---")
    st.subheader("⬇️ Report Generation")
    
    # Export full organizational dataset to CSV
    csv_data = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download Full Organizational Report (.csv)",
        data=csv_data,
        file_name=f"{ORG_NAME}_CarbonCollective_Report_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        key='download_csv'
    )

    # Summary Message with custom styling
    total_co2_saved = df["CO2 Saved (kg)"].sum()
    st.markdown(
        f"""
        <div style="padding: 20px; border-radius: 12px; background-color: #e8f5e9; border: 2px solid #4CAF50;">
            <h4 style="color: #1b5e20; text-align: center; margin-bottom: 5px;">
                **Viksit Bharat 2047 Pledge:**
            </h4>
            <h1 style="color: #2e7d32; text-align: center; margin-top: 0; margin-bottom: 5px;">
                Together, we have saved **{total_co2_saved:,.2f} kg CO₂e**!
            </h1>
            <p style="color: #333; text-align: center; font-size: 1.1em;">
                This demonstrates {ORG_NAME}'s commitment to data-driven green growth and sustainability leadership.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

# --- 5. Main Application Entry Point ---

def main():
    """Sets up the Streamlit page and calls rendering functions."""
    st.set_page_config(
        page_title=APP_TITLE,
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # 1. Initialize data (run once per session)
    initialize_data()
    
    st.title(APP_TITLE)
    st.markdown(f"#### Empowering {ORG_NAME} towards a Sustainable Future")
    
    # New: Render the informative panel explaining credits and Viksit Bharat alignment
    render_informative_panel()
    
    # 2. Render Sidebar Entry Form
    render_sidebar_form()

    # 3. Render Dashboard (Main Panel)
    current_df = st.session_state['carbon_ledger']
    render_main_dashboard(current_df)

    # 4. Render Export Functionality
    render_report_export(current_df)

if __name__ == "__main__":
    main()
