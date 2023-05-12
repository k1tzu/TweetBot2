import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Define the scope and credentials
scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_name('./credentials.json', scope)

class GoogleSheets:
    def __init__(self, google_sheets_key):
        self.google_sheets_key = google_sheets_key

    def get_usernames(self):
        # Authenticate and open the spreadsheet
        gc = gspread.authorize(credentials)
        spreadsheet = gc.open_by_key(self.google_sheets_key)

        # Access a specific sheet within the spreadsheet
        worksheet = spreadsheet.get_worksheet(0)

        # Get all values in the sheet
        values = worksheet.get_all_values()

        twitter_usernames = [row[0].split('/')[-1] for row in values[1:]]

        return twitter_usernames
