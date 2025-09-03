import gspread # type: ignore
import streamlit as st

# Authenticate and connect to Google Sheets    
def get_worksheet(spreadsheet_name, sheet_name):
    """
    Authorizes and opens a Google Sheet using credentials from Streamlit secrets.
    """
    # Authorize with the credentials stored in st.secrets
    creds_dict = st.secrets["gspread"]
    client = gspread.service_account_from_dict(creds_dict)

    # Open the spreadsheet and get the specific worksheet
    spreadsheet = client.open(spreadsheet_name)
    print("✅ Connection successful!")
    print("Data from the spreadsheet:")
    print(spreadsheet.worksheet(sheet_name))
    return spreadsheet.worksheet(sheet_name)

# Read Data from Google Sheets
def read_data():
    worksheet = get_worksheet("testfmc3chat", "Sheet1")
    data = worksheet.get_all_values()  # Get all records from Google Sheet
    return data

# Add Data to Google Sheets
def add_data(row):
    worksheet = get_worksheet("testfmc3chat", "Sheet1")
    worksheet.append_row(row)