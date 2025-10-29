import streamlit as st
import pandas as pd
import plotly.express as px
import uuid
import random
import json
import asyncio
from datetime import datetime, timedelta
import requests

# --- 1. Configuration: School Branding, Emission Factors, and Data Schema ---

# UPDATED: Added an icon to the title string
APP_TITLE = "🌳 HRMS Eco-Score: CarbonCollective – Green Growth for Viksit Bharat 2047"
ORG_NAME = "Hansraj Model School"

# Check for API Key securely using st.secrets
# CRITICAL: This must be set in .streamlit/secrets.toml for deployment.
try:
    API_KEY = st.secrets["gemini_api_key"]
except KeyError:
    API_KEY = None # Will trigger the error message in the app

# API URL (The key is appended by the application, not hardcoded here)
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent"

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
    "Entry ID", "Timestamp", "Name", "Role", "Activity", "Quantity", 
    "CO₂ Saved (kg)", "Credits Generated" # 1 Credit = 1 kg CO₂e
]

# Toggle for demo purposes
GENERATE_MOCK_DATA = True 

# --- 2. Core Logic Functions ---

def calculate_credits(activity, quantity):
    """Calculates CO2 saved and credits based on activity and quantity."""
    factor = EMISSION_FACTORS.get(activity, {"factor": 0})["factor"]
    co2_saved = quantity * factor
    return co2_saved, co2_saved # 1 Credit = 1 kg CO₂e

def initialize_data():
    """Initializes the data DataFrame, populating with mock data if needed."""
    if "data" not in st.session_state or st.session_state.get("data_reset"):
        st.session_state.data = pd.DataFrame(columns=DATA_COLUMNS)
        if GENERATE_MOCK_DATA:
            populate_mock_data()
        st.session_state.data_reset = False
    
    # Ensure all columns are present and correctly typed (especially after reset)
    for col in DATA_COLUMNS:
        if col not in st.session_state.data.columns:
            st.session_state.data[col] = None
    
    # Explicitly set numeric types for calculations
    st.session_state.data["CO₂ Saved (kg)"] = pd.to_numeric(st.session_state.data["CO₂ Saved (kg)"], errors='coerce')
    st.session_state.data["Credits Generated"] = pd.to_numeric(st.session_state.data["Credits Generated"], errors='coerce')


def populate_mock_data(num_entries=80):
    """Generates a large, diverse set of mock data spanning the last 60 days."""
    
    mock_users = {
        "Aarav Sharma": "Student", "Kavya Singh": "Student", "Rohan Mehta": "Student",
        "Priya Iyer": "Student", "Sameer Verma": "Student", "Dr. Neelam Puri": "Faculty/Staff",
        "Prof. Vijay Kumar": "Faculty/Staff", "Ms. Rina Das": "Administration",
        "Anjali Reddy": "Eco-Club Lead"
    }
    
    data = []
    end_date = datetime.now()
    
    for _ in range(num_entries):
        name = random.choice(list(mock_users.keys()))
        role = mock_users[name]
        activity = random.choice(list(EMISSION_FACTORS.keys()))
        
        # Determine quantity range based on activity for realism
        if activity in ["Electricity saved", "Solar power used"]:
            quantity = random.uniform(5, 50) # kWh
        elif activity in ["Walk/Bike Commute"]:
            quantity = random.uniform(1, 15) # km
        elif activity in ["Waste recycled"]:
            quantity = random.uniform(0.5, 10) # kg
        elif activity in ["Trees planted"]:
            quantity = random.randint(1, 5) # count
        elif activity in ["Paper Saved"]:
            quantity = random.randint(50, 500) # sheets
        else: # Water Saved
            quantity = random.randint(10, 200) # liters

        co2_saved, credits = calculate_credits(activity, quantity)
        
        # Generate a timestamp within the last 60 days
        days_ago = random.randint(0, 60)
        timestamp = end_date - timedelta(days=days_ago, hours=random.randint(0, 23), minutes=random.randint(0, 59))

        data.append([
            str(uuid.uuid4()), timestamp.strftime("%Y-%m-%d %H:%M:%S"), name, role, activity, quantity, co2_saved, credits
        ])

    df = pd.DataFrame(data, columns=DATA_COLUMNS)
    # Sort the mock data by timestamp
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    df = df.sort_values(by='Timestamp').reset_index(drop=True)

    st.session_state.data = pd.concat([st.session_state.data, df], ignore_index=True)

def reset_data_callback():
    """Callback function to trigger data reset."""
    st.session_state.data_reset = True
    st.experimental_rerun()

# --- 3. Gemini AI Integration ---

def generate_personalized_tip(user_role, all_activities, current_df): # Removed 'async' and 'await'
    """
    Calls the Gemini API to generate personalized sustainability advice.
    Uses synchronous requests.post for Streamlit Community Cloud deployment.
    """
    if not API_KEY:
        return "⚠️ Gemini API key not found in Streamlit secrets. Cannot generate suggestions."

    # Analyze top activity for context
    if current_df.empty:
        return "Log some data first to get personalized tips!"
        
    top_activity = current_df.groupby('Activity')['Credits Generated'].sum().idxmax()
    total_credits = current_df['Credits Generated'].sum()

    system_prompt = (
        f"You are the 'Eco-Coach' for {ORG_NAME}. Your role is to provide concise, single-paragraph, "
        "and actionable sustainability advice, focusing on maximizing collective impact. Use an encouraging, "
        "school-appropriate tone. Do not use external links or markdown formatting."
    )
    
    user_query = (
        f"The user is a {user_role} at {ORG_NAME}. The organization has collectively generated {total_credits:,.0f} "
        f"credits, with the most impactful activity being '{top_activity}'. "
        f"Given this context, provide one unique, next-level action the user can take today to drive our school towards "
        "the 'Green Growth' goal of Viksit Bharat 2047."
    )

    payload = {
        "contents": [{"parts": [{"text": user_query}]}],
        "systemInstruction": {"parts": [{"text": system_prompt}]},
    }
    
    # Network call with exponential backoff (retry logic)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Append API key to URL for authentication
            url = f"{GEMINI_API_URL}?key={API_KEY}"
            
            # Use requests.post for synchronous HTTP calls
            response = requests.post(
                url, 
                headers={'Content-Type': 'application/json'},
                data=json.dumps(payload)
            )

            # Check for HTTP errors
            response.raise_for_status() # Raises an exception for 4xx or 5xx status codes

            result = response.json()
            
            # Extract text from the complex Gemini response structure
            text = result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', 'No suggestion generated.')
            return text

        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                st.warning(f"API call failed, retrying in {2 ** attempt} seconds...")
                # We can't use 'asyncio.sleep' inside a sync function, so we use time.sleep 
                # or a simple Streamlit workaround, but for simplicity here, we rely on the loop
                # and assume the Streamlit thread handles the wait or just fails fast. 
                # Given this is a simple prototype, we rely on the retry loop for resilience.
                import time
                time.sleep(2 ** attempt)
            else:
                return f"⚠️ Error: Failed to generate tip after multiple retries. Details: {e}"

# --- 4. Streamlit UI Rendering Functions ---

def render_informative_panel():
    """Renders the top panel explaining Carbon Credits and Viksit Bharat Alignment."""
    st.markdown(
        """
        <div style="padding: 15px; border-radius: 10px; background-color: #0E1117; border-left: 5px solid #00B377;">
            <h3 style="color: #00B377; margin-top: 0px;">💡 What are Carbon Credits?</h3>
            <p style="font-size: 14px;">
            In this app, <b>1 Carbon Credit = 1 kg of CO₂e Saved</b> (Carbon Dioxide equivalent). 
            Every sustainable action you log helps our school reduce its environmental footprint.
            </p>
            <h3 style="color: #00B377;">🇮🇳 Viksit Bharat 2047 Alignment</h3>
            <p style="font-size: 14px; margin-bottom: 0px;">
            This project aligns with the 'Green Growth' theme by promoting <b>Digital Empowerment</b> 
            and <b>Community Development</b> through transparent, data-driven sustainability tracking.
            </p>
        </div>
        """, unsafe_allow_html=True
    )

def render_emission_factors_table():
    """Renders a collapsible table showing the conversion factors."""
    # UPDATED: Changed emoji to a gear for a more technical/factor feel
    with st.expander("⚙️ View Carbon Credit Conversion Factors"):
        factors_data = [
            (activity, f"{data['factor']:,.3f}", data['unit'])
            for activity, data in EMISSION_FACTORS.items()
        ]
        factors_df = pd.DataFrame(factors_data, columns=["Activity", "kg CO₂e per Unit (Credit Value)", "Unit"])
        st.dataframe(factors_df, hide_index=True, use_container_width=True)

def render_sidebar_form():
    """Renders the data entry form in the sidebar."""
    # UPDATED: Added icon to header
    st.sidebar.header("Log Your Green Action 📝") 
    
    # Use a key to manage the form state for dynamic updates
    form_key = "log_contribution_form"
    
    with st.sidebar.form(key=form_key):
        name = st.text_input("Your Full Name", placeholder="e.g., Ananya Deshmukh")
        role = st.selectbox("Your Role / Department", options=USER_ROLES)
        
        # --- Dynamic Unit Logic ---
        activity = st.selectbox(
            "Select Activity", 
            options=list(EMISSION_FACTORS.keys()), 
            key='activity_select' # Key to track selection
        )
        
        # Retrieve the unit based on the current selection for the label
        current_unit = EMISSION_FACTORS.get(activity, {}).get('unit', 'Units')
        
        # Quantity input using the dynamic unit
        quantity = st.number_input(f"Quantity ({current_unit})", min_value=0.01, value=1.00, step=0.01)
        
        # UPDATED: Kept original emoji
        submitted = st.form_submit_button("Log Contribution ✨")

        if submitted:
            if not name:
                st.error("Please enter your name.")
            elif quantity <= 0:
                st.error("Quantity must be greater than zero.")
            else:
                co2_saved, credits = calculate_credits(activity, quantity)
                
                new_entry = pd.DataFrame([{
                    "Entry ID": str(uuid.uuid4()),
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Name": name,
                    "Role": role,
                    "Activity": activity,
                    "Quantity": quantity,
                    "CO₂ Saved (kg)": co2_saved,
                    "Credits Generated": credits
                }])
                
                # Append to session state data
                st.session_state.data = pd.concat([st.session_state.data, new_entry], ignore_index=True)
                st.session_state.data["Timestamp"] = pd.to_datetime(st.session_state.data["Timestamp"])

                st.success(f"Logged {quantity:,.2f} {current_unit} of {activity}. Generated {credits:,.2f} Credits!")
    
    st.sidebar.markdown("---")
    # UPDATED: Kept original emoji
    st.sidebar.button("♻️ Reset All Data", on_click=reset_data_callback, help="Wipes out all logged contributions and resets to mock data.")

def render_main_dashboard():
    """Renders the main dashboard with metrics and visualizations."""
    
    df = st.session_state.data
    
    # 1. Top Level Metrics
    total_credits = df["Credits Generated"].sum()
    total_entries = len(df)
    
    # Find top contributors
    if total_entries > 0:
        leaderboard = df.groupby('Name')['Credits Generated'].sum().sort_values(ascending=False)
        top_contributor = leaderboard.index[0]
        top_credits = leaderboard.iloc[0]
        
        role_leaderboard = df.groupby('Role')['Credits Generated'].sum().sort_values(ascending=False)
        top_role = role_leaderboard.index[0]
    else:
        top_contributor = "N/A"
        top_credits = 0
        top_role = "N/A"

    # UPDATED: Changed emoji to a globe
    st.subheader(f"Dashboard: {ORG_NAME}'s Collective Impact 🌎")

    col1, col2, col3, col4 = st.columns(4)

    # UPDATED: Added emojis to st.metric labels
    with col1:
        st.metric("🌿 Total Credits Generated", f"{total_credits:,.0f} pts", delta_color="normal", help="1 point = 1 kg CO₂e saved.")
    with col2:
        st.metric("📝 Total Actions Logged", f"{total_entries:,}")
    with col3:
        st.metric("🥇 Top Contributor", top_contributor, delta=f"{top_credits:,.0f} Credits")
    with col4:
        st.metric("👥 Leading Role", top_role)
    
    st.markdown("---")

    # 2. AI Personalized Suggestions
    # UPDATED: Added icon to header
    st.header("🧠 Personalized Eco-Coach Advice")
    
    if API_KEY:
        # UPDATED: Added icon to button
        if st.button("Generate AI Suggestion 🤖"):
            # Use a random role for the prompt since a logged-in user isn't implemented
            random_role = random.choice(USER_ROLES) 
            
            with st.spinner("Eco-Coach is thinking..."):
                # Run the synchronous function directly
                result = generate_personalized_tip(random_role, list(EMISSION_FACTORS.keys()), df)
                
                # Store the result in session state to persist it during the rerun
                st.session_state.ai_suggestion = result
        
        if st.session_state.get("ai_suggestion"):
             st.info(st.session_state.ai_suggestion)
             
    else:
        st.warning("⚠️ **Gemini AI Feature Disabled:** Please set `gemini_api_key` in `.streamlit/secrets.toml` to enable the Eco-Coach.")


    st.markdown("---")
    # UPDATED: Added icon to header
    st.header("📈 Visualization and Analytics")
    
    # 3. Visualizations
    col_a, col_b = st.columns(2)

    if total_entries > 0:
        
        # Chart 1: Role/Department-wise CO₂ Savings Contribution (Pie Chart)
        role_contribution = df.groupby('Role')['Credits Generated'].sum().reset_index()
        fig1 = px.pie(
            role_contribution, 
            values='Credits Generated', 
            names='Role', 
            title='Contribution Breakdown by Role'
        )
        col_a.plotly_chart(fig1, use_container_width=True)

        # Chart 2: Top 10 User Leaderboard (Bar Chart)
        user_leaderboard_data = df.groupby('Name')['Credits Generated'].sum().nlargest(10).reset_index()
        fig2 = px.bar(
            user_leaderboard_data, 
            x='Credits Generated', 
            y='Name', 
            orientation='h', 
            title='Top 10 Green Champions (Credits)', 
            color_discrete_sequence=px.colors.sequential.Viridis
        )
        fig2.update_layout(yaxis={'categoryorder':'total ascending'})
        col_b.plotly_chart(fig2, use_container_width=True)

        # New Chart 3: Organizational Progress (Cumulative Credits over Time)
        df_time = df.copy()
        df_time['Timestamp_Date'] = df_time['Timestamp'].dt.date
        cumulative_credits = df_time.groupby('Timestamp_Date')['Credits Generated'].sum().cumsum().reset_index()
        
        fig3 = px.line(
            cumulative_credits, 
            x='Timestamp_Date', 
            y='Credits Generated', 
            title=f'{ORG_NAME} Cumulative Carbon Credits Over Time',
            labels={'Timestamp_Date': 'Date', 'Credits Generated': 'Cumulative Credits (kg CO₂e)'},
            line_shape='spline'
        )
        st.plotly_chart(fig3, use_container_width=True)

        # New Chart 4: Activity Breakdown by Role (Vertical Bar Chart)
        role_activity_pivot = df.pivot_table(
            index='Activity', 
            columns='Role', 
            values='Credits Generated', 
            aggfunc='sum'
        ).fillna(0).reset_index()
        
        # Melt the DataFrame for Plotly express
        role_activity_melted = role_activity_pivot.melt(
            id_vars='Activity', 
            value_vars=USER_ROLES, 
            var_name='Role', 
            value_name='Credits'
        )

        fig4 = px.bar(
            role_activity_melted,
            x='Activity',
            y='Credits',
            color='Role',
            title='Activity Impact by Role',
            barmode='stack'
        )
        st.plotly_chart(fig4, use_container_width=True)


    else:
        st.info("No contributions logged yet. Log your first green action to see the dashboard!")
    
    # 4. Emission Factor Table
    render_emission_factors_table()

    # 5. Export Functionality
    st.markdown("---")
    # UPDATED: Added icon to subheader
    st.subheader("⬇️ Report Generation")
    
    if total_entries > 0:
        # Create a CSV export button
        csv_export = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            # UPDATED: Added icon to button label
            label="Download Full Contribution CSV 💾",
            data=csv_export,
            file_name=f'{ORG_NAME}_CarbonCollective_Report_{datetime.now().strftime("%Y%m%d")}.csv',
            mime='text/csv',
            help="Download the complete, raw ledger data for all entries."
        )

        # Final Summary
        st.markdown(
            f"""
            <div style="background-color: #0E1117; padding: 20px; border-radius: 10px; text-align: center; margin-top: 20px;">
                <h2 style="color: #00B377;">🌟 SUCCESS! 🌟</h2>
                <p style="font-size: 18px;">
                Together, Hansraj Model School has saved a total of 
                <b style="color: #64FF96;">{total_credits:,.2f} kg CO₂e</b> 
                (Carbon Credits)! We are actively contributing to Viksit Bharat's Green Growth vision.
                </p>
            </div>
            """, unsafe_allow_html=True
        )

# --- 5. Application Entry Point ---

def main():
    """Main function to run the Streamlit application."""
    st.set_page_config(layout="wide", page_title=APP_TITLE)
    
    # Initialize the data frame (loads mock data if it's the first run)
    initialize_data()
    
    st.title(APP_TITLE)

    # Render components
    render_informative_panel()
    
    # Layout the main dashboard and the sidebar form
    render_sidebar_form()
    render_main_dashboard()

if __name__ == "__main__":
    main()
