# gsc_wrapper.py
import datetime
import pandas as pd
import gsc_weekly_report

def generate_report(start_date, end_date, property_url=None, credentials_path=None):
    """
    Call the real generate_report in gsc_weekly_report and re-raise any exception
    so we can see errors in Streamlit / terminal.
    """
    # Normalize dates
    if hasattr(start_date, "isoformat"):
        sd = start_date
    else:
        sd = start_date
    if hasattr(end_date, "isoformat"):
        ed = end_date
    else:
        ed = end_date

    # Direct call to your function (do not swallow exceptions)
    try:
        return gsc_weekly_report.generate_report(sd, ed, property_url=property_url, credentials_path=credentials_path)
    except Exception as e:
        # Re-raise so Streamlit shows the full traceback
        raise
