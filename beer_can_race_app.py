import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, time
import pydeck as pdk

# --- INSTRUCTIONS ---
st.markdown("""
### Beer Can Scrimmage Race Log
Welcome! Please enter your race data below:
- **Start/Finish Times**: Use 24-hour format. Start time from **18:00**, finish from **19:00**, in 1-minute increments.
- **Island Marks**: Select the marks in the order rounded (up to 6). Islands may appear more than once.
- **Points System**:
  - 1 boat: 1 point
  - 2 boats: 2/1 for 1st/2nd
  - 3+ boats: 3/2/1 for top 3, and 1 point for other finishers

Have fun and sail safe!
""")

# --- AUTHENTICATION ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
client = gspread.authorize(creds)
sheet = client.open_by_url(st.secrets["private_gsheets_url"]).worksheet("Race Entries")

# --- ISLANDS ON LAKE RAMSEY ---
islands = ["Island A", "Island B", "Gull Rock", "Bell Island", "The Sisters", "White Rocks", "Goat Island", "Ramsey Point", "Canoe Point"]

# --- RACE FORM ---
st.header("Log a Race Result")
with st.form("race_form"):
    race_date = st.date_input("Race Date", datetime.today())
    boat_name = st.text_input("Boat Name")
    skipper = st.text_input("Skipper")
    boat_type = st.text_input("Boat Type")

    start_time = st.time_input("Start Time", time(18, 0), step=60)
    finish_time = st.time_input("Finish Time", time(19, 0), step=60)

    elapsed = st.number_input("Elapsed Time (minutes)", min_value=1)
    corrected = st.number_input("Corrected Time (minutes)", min_value=1)

    marks = [st.selectbox(f"Mark {i+1}", islands, key=f"mark_{i}") for i in range(6)]

    protest = st.radio("Any Protests?", ["N", "Y"])
    wind = st.selectbox("Wind Conditions", ["Drifter", "Light Air", "Moderate Breeze", "Strong Breeze"])
    comments = st.text_area("Comments / Suggestions")

    submitted = st.form_submit_button("Submit")
    if submitted:
        row = [race_date, boat_name, skipper, boat_type, start_time.strftime("%H:%M"), finish_time.strftime("%H:%M"),
               elapsed, corrected, *marks, protest, wind, comments]
        sheet.append_row(row)
        st.success("Entry recorded successfully!")

# --- LOAD DATA ---
data = sheet.get_all_values()
df = pd.DataFrame(data[1:], columns=data[0])
df["Corrected Time"] = pd.to_numeric(df["Corrected Time"], errors="coerce")
df["Race Date"] = pd.to_datetime(df["Race Date"], errors="coerce")

# --- WEEKLY LEADERBOARD ---
st.header("Weekly Leaderboard")
selected_date = st.date_input("Select Friday Race Date", datetime.today())
weekly = df[df["Race Date"] == pd.to_datetime(selected_date)]

if not weekly.empty:
    weekly_sorted = weekly.sort_values("Corrected Time")
    count = len(weekly_sorted)
    base_points = [4, 3, 2] if count >= 5 else ([3, 2, 1][:count] if count >= 3 else list(range(count, 0, -1)))
    base_points += [1] * max(0, count - len(base_points))
    weekly_sorted["Points"] = base_points
    st.dataframe(weekly_sorted[["Skipper", "Boat Name", "Corrected Time", "Points"]])

    # --- CUMULATIVE STANDINGS ---
    st.header("Season Standings")
    all_scores = df[df["Corrected Time"].notna()]
    all_scores = all_scores.sort_values(["Race Date", "Corrected Time"])
    all_points = []
    for date in all_scores["Race Date"].unique():
        races = all_scores[all_scores["Race Date"] == date]
        pts = [4, 3, 2] if len(races) >= 5 else ([3, 2, 1][:len(races)] if len(races) >= 3 else list(range(len(races), 0, -1)))
        pts += [1] * max(0, len(races) - len(pts))
        temp = races.copy()
        temp["Points"] = pts
        all_points.append(temp)
    season = pd.concat(all_points)
    season_total = season.groupby("Skipper")["Points"].sum().reset_index().sort_values("Points", ascending=False)
    st.dataframe(season_total)
else:
    st.info("No race data found for selected date.")
