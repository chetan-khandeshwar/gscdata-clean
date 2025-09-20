# app.py
import os
import json
import datetime as dt
from pathlib import Path

import streamlit as st

# try to import the report generator we included
try:
    from gsc_weekly_report import generate_report, get_service_from_credentials
except Exception:
    # If running on Streamlit Cloud, module must be in repo root as gsc_weekly_report.py
    raise

st.set_page_config(page_title="GSC Weekly Report All Sites", layout="wide")
st.title("📊  GSC Weekly Report All Sites")

st.markdown(
    "This app lets each user sign in with their Google account and select properties "
    "they have access to in Search Console."
)

# -----------------------------
# Helpers: credentials detection
# -----------------------------
def load_client_secret_from_streamlit_secrets():
    """Return dict or None"""
    cs = st.secrets.get("client_secret_json")
    if cs:
        # If secrets contains the JSON object already
        if isinstance(cs, dict):
            return cs
        # Or a string stored in secrets
        try:
            return json.loads(cs)
        except Exception:
            return None
    return None


def load_client_secret_from_file():
    p = Path("client_secret.json")
    if p.exists():
        with p.open("r", encoding="utf8") as fh:
            return json.load(fh)
    return None


def get_client_secret():
    # 1. prefer streamlit secrets (for Cloud)
    cs = load_client_secret_from_streamlit_secrets()
    if cs:
        return cs
    # 2. fallback to local file (for local dev)
    cs = load_client_secret_from_file()
    if cs:
        return cs
    return None


client_secret = get_client_secret()
if not client_secret:
    st.warning(
        "No OAuth client config found in Streamlit secrets or client_secret.json file. "
        "Add `client_secret_json` to Streamlit secrets or place a `client_secret.json` file in the project root."
    )

# --------------------------------
# Date controls and quick range UI
# --------------------------------
today = dt.date.today()
DEFAULT_RANGE_DAYS = 7

# initialize session state keys
if "range_days" not in st.session_state:
    st.session_state.range_days = DEFAULT_RANGE_DAYS
if "start_date" not in st.session_state:
    st.session_state.start_date = today - dt.timedelta(days=DEFAULT_RANGE_DAYS - 1)
if "end_date" not in st.session_state:
    st.session_state.end_date = today

def set_range(n):
    st.session_state.range_days = n
    st.session_state.start_date = today - dt.timedelta(days=n - 1)
    st.session_state.end_date = today
    # no experimental_rerun - streamlit will re-run automatically when state changes

# layout
col1, col2 = st.columns([4, 3])
with col1:
    start = st.date_input("Start date", value=st.session_state.start_date, key="ui_start_date")
with col2:
    end = st.date_input("End date", value=st.session_state.end_date, key="ui_end_date")

# Quick buttons row
c1, c2, c3 = st.columns(3)
with c1:
    st.button("7 Days", on_click=set_range, args=(7,))
with c2:
    st.button("28 Days", on_click=set_range, args=(28,))
with c3:
    st.button("90 Days", on_click=set_range, args=(90,))

# sync UI changes back to session_state (if user typed a custom date)
st.session_state.start_date = st.session_state.get("ui_start_date", st.session_state.start_date)
st.session_state.end_date = st.session_state.get("ui_end_date", st.session_state.end_date)

# row limit
row_limit = st.number_input("Row limit per query", min_value=1000, max_value=250000, value=25000, step=1000)

st.write("---")

# ---------------------
# style the Generate button (light red)
# ---------------------
st.markdown(
    """
    <style>
    /* style the last button (Generate) to be light red */
    .generate-btn > button {
        background: #f8d7da !important;
        color: #611a1d !important;
        border: 1px solid rgba(98,0,0,0.08) !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ----------------------
# Authentication section
# ----------------------
st.header("Sign in with Google to access your Search Console data")

if client_secret:
    st.info("OAuth client configuration found.")
else:
    st.error("Missing OAuth client configuration in secrets; cannot start authentication.")

# ---------------------
# Action: Generate Report
# ---------------------
def on_generate():
    # ensure we have credentials
    if not client_secret:
        st.error("Cannot run: no OAuth client config found. Add client_secret.json or add to Streamlit secrets.")
        return

    start_dt = st.session_state.start_date
    end_dt = st.session_state.end_date

    with st.spinner("Fetching site summaries from Google Search Console..."):
        try:
            # generate_report should handle auth using client_secret dict or file
            df = generate_report(client_secret=client_secret, start_date=start_dt, end_date=end_dt, row_limit=row_limit)
            st.success("Report generated.")
            st.dataframe(df)
        except Exception as exc:
            st.exception(exc)


# Put the generate button in a container we can style:
gen_col1, gen_col2 = st.columns([1, 3])
with gen_col1:
    # wrapper to attach CSS class
    st.markdown('<div class="generate-btn">', unsafe_allow_html=True)
    if st.button("Generate Report (sites.txt)"):
        on_generate()
    st.markdown("</div>", unsafe_allow_html=True)


# small debug panel (only visible to dev)
if st.checkbox("Show debug info"):
    st.write("session_state:", dict(st.session_state))
    st.write("client_secret present:", bool(client_secret))

