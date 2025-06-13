# Beer Can Scrimmage - redeploy trigger.

import streamlit as st
import pandas as pd
import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from PIL import Image
import io

# --- CONFIG ---
SPREADSHEET_NAME = "Beer Can Scrimmage Tracker"
SHEET_NAME = "Race Entries"
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/10ON_p0Y_yxa-o0W_4_oDc9muB32WOeyJ-bS0H5Nt-AQ"

# --- AUTHENTICATION ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets["gcp_service_account"]), scope)
client = gspread.authorize(creds)
sheet = client.open_by_url(GOOGLE_SHEET_URL).worksheet(SHEET_NAME)

# --- HANDICAP RATINGS ---
ratings = {
    "Sirius 21": 240,
    "Hobie 16": 215
}

# --- FORM ---
st.title("⛵ Beer Can Scrimmage Entry Log")
st.markdown("Log your race entry below. All fields required.")

with st.form("entry_form"):
    date = st.date_input("Race Date", value=datetime.date.today())
    boat_name = st.selectbox("Boat Name", ["V&G", "Claire the Cat"])
    skipper = st.selectbox("Skipper", ["Steven Knight", "Heather Knight"])
    model = st.selectbox("Make & Model", ["Sirius 21", "Hobie 16"])
    start_time = st.time_input("Start Time", value=datetime.time(0, 0), step=60)
    finish_time = st.time_input("Finish Time", value=datetime.time(0, 0), step=60)
    wind_direction = st.selectbox("Wind Direction", ["N", "NE", "E", "SE", "S", "SW", "W", "NW"])

    all_marks = [
        "Whitewater Island", "Duck Island", "Ramsey Lake Island", "Blueberry Island",
        "Doctor's Island", "Minnow Island", "South Ramsey Island", "Hospital Island",
        "Laurentian University Island", "Big Island", "Small Island", "Goose Island"
    ]
    marks = st.multiselect("Marks Rounded (in order, allow repeats)", all_marks)
    weather = st.multiselect("Weather Conditions", ["Calm", "Light Air", "Breezy", "Windy", "Gusty", "Rain", "Fog", "Cold", "Hot"])
    photo = st.file_uploader("Upload Photo (optional)", type=["jpg", "jpeg", "png"])
    submitted = st.form_submit_button("Submit Entry")

    if submitted:
        elapsed = datetime.datetime.combine(date, finish_time) - datetime.datetime.combine(date, start_time)
        elapsed_minutes = elapsed.total_seconds() / 60
        rating = ratings.get(model, 220)
        corrected = elapsed_minutes * (100 / rating)

        row = [
            str(date), boat_name, skipper, model,
            start_time.strftime("%H:%M"), finish_time.strftime("%H:%M"),
            round(elapsed_minutes, 2), round(corrected, 2),
            ", ".join(marks), wind_direction, ", ".join(weather)
        ]

        sheet.append_row(row)
        st.success("Entry logged! Check the leaderboard below.")

# --- LEADERBOARD ---
st.header("🏁 Leaderboard")
data = sheet.get_all_values()

if not data or len(data) <= 1:
    st.info("No race entries yet. Be the first!")
else:
    headers = data[0]
    rows = data[1:]
    df = pd.DataFrame(rows, columns=headers)
    df["Corrected Time"] = pd.to_numeric(df["Corrected Time"], errors='coerce')
    df["Date"] = pd.to_datetime(df["Date"], errors='coerce')

    race_dates = df["Date"].dt.date.unique()
    friday_dates = [d for d in race_dates if d.weekday() == 4]

    selected_friday = st.selectbox("Select Friday Race Date", sorted(friday_dates, reverse=True))

    if selected_friday:
        weekly_df = df[df["Date"].dt.date == selected_friday]
        weekly_df = weekly_df.sort_values("Corrected Time")
        st.subheader(f"Results for {selected_friday}")
        st.dataframe(weekly_df)

        scored = weekly_df.copy()
        scored["Points"] = [3 if i == 0 else 2 if i == 1 else 1 if i == 2 else 0 for i in range(len(scored))]

        points_table = scored.groupby("Skipper")["Points"].sum().reset_index()
        points_table = points_table.sort_values("Points", ascending=False)

        st.subheader("🏆 Annual Standings")
        st.dataframe(points_table)
