from flask import Flask, make_response
from datetime import datetime
import pytz
from supabase import create_client
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json

app = Flask(__name__)

# Supabase client
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.route("/")
def track_and_redirect():
    # ✅ 1. Return styled HTML *immediately*
    response = make_response(f"""
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>잠시만 기다려 주세요...</title>
        <meta http-equiv="refresh" content="2; url={os.environ['TARGET_URL']}">
        <style>
        body {{
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            font-family: sans-serif;
            font-size: 1.5rem;
            background: #f7f7f7;
        }}
        </style>
    </head>
    <body>
        <p>잠시만 기다려 주세요...</p>
    </body>
    </html>
    """)

    # ✅ 2. Use Sydney timezone for correct date
    sydney = pytz.timezone("Australia/Sydney")
    today = datetime.now(sydney).date().isoformat()  # e.g. "2025-06-23"

    # ✅ 3. Atomically increment count via Supabase stored procedure
    supabase.rpc("increment_daily_count", {"in_date": today}).execute()

    # ✅ 4. Get total count for today
    result = supabase.table("daily_visits").select("*").eq("date", today).single().execute()
    count = result.data["count"]

    # ✅ 5. Update Google Sheets
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        json.loads(os.environ["GOOGLE_CREDS"]),
        ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    )
    client = gspread.authorize(creds)
    sheet = client.open("visitors-e").sheet1

    # Update cell B1 (or wherever you want)
    sheet.update_acell("B1", count)

    return response