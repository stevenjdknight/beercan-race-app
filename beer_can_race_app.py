import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, time

# --- PAGE CONFIG ---
st.set_page_config(page_title="Beer Can Scrimmage", layout="wide")
st.title("🍺 Beer Can Scrimmage Race Log")

# --- INSTRUCTIONS ---
st.markdown("""
Enter your race details below.

- Start time defaults to 18:00, finish time to 19:00.
- You can round up to 6 marks — duplicates allowed.
- Points system:
  - 1 boat: 1 point
  - 2 boats: 2/1
  - 3+ boats: 3/2/1 for top 3, others get 1
""")

# --- GOOGLE SHEETS AUTH ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
try:
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        st.secrets["gcp_service_account"], scope)
    client = gspread.authorize(creds)
    sheet_url = st.secrets["private_gsheets_url"].split("/edit")[0]
    worksheet = client.open_by_url(sheet_url).worksheet("Race Entries")
except Exception as e:
    st.error(f"Error accessing Google Sheet: {e}")
    st.stop()

# --- ISLAND MARK OPTIONS ---
islands = ["Island A", "Island B", "Gull Rock", "Bell Island", "The Sisters",
           "White Rocks", "Goat Island", "Ramsey Point", "Canoe Point"]

# --- FORM ENTRY ---
with st.form("race_form"):
    st.subheader("Log a Race Result")

    race_date = st.date_input("Race Date", value=datetime.today())
    boat_name = st.text_input("Boat Name")
    skipper = st.text_input("Skipper")
    boat_type = st.text_input("Boat Type")
    start_time = st.time_input("Start Time", value=time(18, 0), step=60)
    finish_time = st.time_input("Finish Time", value=time(19, 0), step=60)

    elapsed = st.number_input("Elapsed Time (min)", min_value=1)
    corrected = st.number_input("Corrected Time (min)", min_value=1)

    marks = [st.selectbox(f"Mark {i+1}", islands, key=f"mark_{i}") for i in range(6)]

    comments = st.text_area("Comments or Improvements")

    submitted = st.form_submit_button("Submit Race")

    if submitted:
        try:
            worksheet.append_row([
                str(race_date), boat_name, skipper, boat_type,
                start_time.strftime("%H:%M"), finish_time.strftime("%H:%M"),
                elapsed, corrected, *marks, comments
            ])
            st.success("Race submitted successfully!")
        except Exception as e:
            st.error(f"Error submitting race: {e}")
