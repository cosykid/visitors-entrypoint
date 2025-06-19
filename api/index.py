from flask import Flask, redirect
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json
import pytz

app = Flask(__name__)

def to_sheets_serial(dt):
    epoch = datetime(1899, 12, 30, tzinfo=dt.tzinfo)
    delta = dt - epoch
    return delta.total_seconds() / 86400  # float: days since epoch

@app.route("/")
def track_and_redirect():
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

    try:
        records = sheet.get_all_records()
    except IndexError:
        records = []

    for i, row in enumerate(records, start=2):
        if row.get("date") == today_str:
            current_count = int(row.get("count", 0))
            sheet.update_cell(i, 2, current_count + 1)
            break
    else:
        sheet.append_row([today_serial, 1])

    return redirect(os.environ["TARGET_URL"])

if __name__ == "__main__":
    app.run(debug=True)
