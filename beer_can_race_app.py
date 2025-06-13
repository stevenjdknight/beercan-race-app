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
    start_time = st.time_input("Start Time", value=datetime.datetime.now().time())
    finish_time = st.time_input("Finish Time", value=datetime.datetime.now().time())
    wind_direction = st.selectbox("Wind Direction", ["N", "NE", "E", "SE", "S", "SW", "W", "NW"])
    marks = st.multiselect(
        "Marks Rounded (in order)",
        ["Island A", "Island B", "Island C", "Island D", "Island E", "Big Channel", "North Mark", "South Bay"],
        help="Select the order of islands rounded; duplicates allowed."
    )
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
data = sheet.get_all_records()
df = pd.DataFrame(data)

if not df.empty:
    # Sort by selected race date (Fridays only)
    df["Date"] = pd.to_datetime(df["Date"])
    fridays = df[df["Date"].dt.dayofweek == 4]["Date"].drop_duplicates().sort_values(ascending=False)
    selected_date = st.selectbox("Select Friday race date", fridays.dt.strftime("%Y-%m-%d"))
    selected_df = df[df["Date"] == pd.to_datetime(selected_date)]

    # Score system: 3-2-1 for top 3 corrected times
    scored = selected_df.copy().sort_values("Corrected Time").reset_index(drop=True)
    scored["Points"] = [3, 2, 1] + [0] * max(0, len(scored) - 3)

    st.subheader("📋 Weekly Results")
    st.dataframe(scored)

    # --- Annual Leaderboard ---
    st.subheader("🏆 Annual Standings")
    all_scores = df.copy()
    all_scores["Date"] = pd.to_datetime(all_scores["Date"])
    all_scores = all_scores[all_scores["Date"].dt.dayofweek == 4]  # Fridays only
    all_scores = all_scores.sort_values(["Date", "Corrected Time"])

    def assign_points(group):
        pts = [3, 2, 1] + [0] * max(0, len(group) - 3)
        group["Points"] = pts
        return group

    grouped = all_scores.groupby("Date", group_keys=False).apply(assign_points)
    season_scores = grouped.groupby("Skipper")["Points"].sum().reset_index().sort_values("Points", ascending=False)
    st.dataframe(season_scores)
else:
    st.info("No race entries yet. Be the first!")
