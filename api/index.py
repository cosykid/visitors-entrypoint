from flask import Flask, make_response
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from supabase import create_client
import os
import json
import pytz

app = Flask(__name__)


# Supabase client
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def to_sheets_serial(dt):
    epoch = datetime(1899, 12, 30, tzinfo=dt.tzinfo)
    delta = dt - epoch
    return delta.total_seconds() / 86400  # float: days since epoch

@app.route("/")
def track_and_redirect():
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

    # Google Sheets auth
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(os.environ["GOOGLE_CREDS"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open("visitors-entrypoint").sheet1

    # Get Sydney datetime
    sydney = pytz.timezone("Australia/Sydney")
    now = datetime.now(sydney)

    # For matching (Sheets returns date as YYYY-MM-DD string in get_all_records)
    today_str = now.strftime("%d/%m/%Y")
    today_serial = to_sheets_serial(now)

    today = datetime.now(sydney).date().isoformat()

    supabase.rpc("increment_daily_count", {"in_date": today}).execute()
    result = supabase.table("daily_visits").select("*").eq("date", today).single().execute()
    count = result.data["count"]

    try:
        records = sheet.get_all_records()
    except IndexError:
        records = []

    for i, row in enumerate(records, start=2):
        if row.get("date") == today_str:
            current_count = int(row.get("count", 0))
            sheet.update_cell(i, 2, int(count))
            break
    else:
        sheet.append_row([today_serial, 1])

    return response

if __name__ == "__main__":
    app.run(debug=True)
