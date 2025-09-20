# app.py
import json
import urllib.parse
from typing import Optional

import streamlit as st

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from gsc_weekly_report import (
    get_service_from_credentials,
    generate_report,
)

# Scopes we need for Search Console readonly / analytics
SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]

st.set_page_config(page_title="GSC Weekly Report All Sites", layout="wide")

st.title("GSC Weekly Report All Sites")
st.markdown(
    "This app lets each user sign in with their Google account and select properties they have access to in Search Console."
)

# ---- load client config JSON from st.secrets ----
client_secret_json = None
if "client_secret_json" in st.secrets:
    # secrets stores the literal JSON string (user will paste the whole client_secret.json contents)
    try:
        client_secret_json = json.loads(st.secrets["client_secret_json"])
    except Exception as e:
        st.error("Unable to parse client_secret_json from secrets. Make sure you pasted the entire client_secret.json.")
else:
    st.warning(
        "No OAuth client config found in Streamlit secrets. Add client_secret_json to Secrets (paste the JSON)."
    )

# helper: current URL to use as redirect URI
def _current_url():
    # streamlit exposes query params; but we need the base URL for redirect
    # Streamlit sets the app hostname — we use window.location in JS normally, but Flow can accept the Streamlit URL path
    # We'll use http://localhost:8501 for local testing; in Cloud the redirect URIs should be registered already.
    base = st.experimental_get_query_params().get("_", [None])[0]
    if base:
        return base
    # fallback to localhost - OAuth redirect URIs must match registered ones
    return "http://localhost:8501/"

# Build client config suitable for google_auth_oauthlib
def build_client_config():
    if client_secret_json is None:
        return None
    # client_secret_json is normally in the "installed" or "web" key depending on type
    if "web" in client_secret_json:
        return client_secret_json
    if "installed" in client_secret_json:
        # adapt installed => web
        return {
            "web": {
                "client_id": client_secret_json["installed"]["client_id"],
                "client_secret": client_secret_json["installed"]["client_secret"],
                "auth_uri": client_secret_json["installed"]["auth_uri"],
                "token_uri": client_secret_json["installed"]["token_uri"],
                "redirect_uris": client_secret_json["installed"].get("redirect_uris", []),
            }
        }
    # else assume it's already a web config
    return client_secret_json

client_config = build_client_config()

# session storage keys
CRED_KEY = "gsc_credentials"

# -------- OAuth flow handling ----------
query_params = st.experimental_get_query_params()
code = query_params.get("code", [None])[0]
state = query_params.get("state", [None])[0]

# If user already has credentials in session, use them
creds: Optional[Credentials] = st.session_state.get(CRED_KEY)

# If we received an authorization 'code' from Google's redirect, finish the flow
if code and client_config and not creds:
    try:
        redirect_uri = _current_url()
        flow = Flow.from_client_config(client_config=client_config, scopes=SCOPES, redirect_uri=redirect_uri)
        # If Google returned 'state' Streamlit will provide it; pass the full query string to fetch_token
        # flow.fetch_token expects either code or authorization_response
        # We prefer to use the full current URL with code param:
        url = st.experimental_get_query_params()
        # Build full redirect URL received by the browser:
        # Streamlit doesn't provide full hostname easily - google will accept the code when the redirect URI matches what's registered.
        authorization_response = st.experimental_get_query_params()
        # Simpler: use the current page URL (browser) as authorization_response:
        # Build auth response from raw query string present in the browser location (streamlit doesn't provide it directly).
        # We'll reconstruct from request parts:
        # The fetch_token can accept code directly:
        flow.fetch_token(code=code)
        creds = flow.credentials
        st.session_state[CRED_KEY] = creds_to_dict(creds := creds)
        st.experimental_rerun()
    except Exception as e:
        st.error("OAuth token exchange failed. Try authenticating again (click the 'Sign in' link).")
        st.exception(e)

# small helper to convert Credentials <-> dict
def creds_to_dict(c: Credentials):
    return {
        "token": c.token,
        "refresh_token": c.refresh_token,
        "token_uri": c.token_uri,
        "client_id": c.client_id,
        "client_secret": c.client_secret,
        "scopes": c.scopes,
    }

def creds_from_dict(d: dict) -> Credentials:
    return Credentials(
        token=d.get("token"),
        refresh_token=d.get("refresh_token"),
        token_uri=d.get("token_uri"),
        client_id=d.get("client_id"),
        client_secret=d.get("client_secret"),
        scopes=d.get("scopes"),
    )

# If saved in session as dict, convert to Credentials
if isinstance(st.session_state.get(CRED_KEY), dict):
    try:
        creds = creds_from_dict(st.session_state.get(CRED_KEY))
    except Exception:
        creds = None

# Authentication UI
st.markdown("### Sign in with Google to access your Search Console data")
col1, col2 = st.columns([1, 3])
with col1:
    if creds and creds.valid:
        st.success("Authenticated ✅")
        if st.button("Sign out"):
            st.session_state.pop(CRED_KEY, None)
            st.experimental_rerun()
    else:
        if client_config is None:
            st.info("Missing OAuth client configuration in secrets; cannot start authentication.")
        else:
            # Build Flow to create an authorization URL
            redirect_uri = _current_url()
            flow = Flow.from_client_config(client_config=client_config, scopes=SCOPES, redirect_uri=redirect_uri)
            auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline", include_granted_scopes="true")
            st.markdown(f"[Click here to authenticate]({auth_url})", unsafe_allow_html=True)

# Date range controls + row limit
st.markdown("---")
c1, c2 = st.columns(2)
with c1:
    start_date = st.date_input("Start date")
with c2:
    end_date = st.date_input("End date")

period_col1, period_col2, period_col3 = st.columns([1, 1, 1])
with period_col1:
    if st.button("7 Days"):
        import datetime

        st.session_state["start_date"] = (datetime.date.today() - datetime.timedelta(days=6))
        st.session_state["end_date"] = datetime.date.today()
        st.experimental_rerun()
with period_col2:
    if st.button("28 Days"):
        import datetime

        st.session_state["start_date"] = (datetime.date.today() - datetime.timedelta(days=27))
        st.session_state["end_date"] = datetime.date.today()
        st.experimental_rerun()
with period_col3:
    if st.button("90 Days"):
        import datetime

        st.session_state["start_date"] = (datetime.date.today() - datetime.timedelta(days=89))
        st.session_state["end_date"] = datetime.date.today()
        st.experimental_rerun()

row_limit = st.number_input("Row limit per query", min_value=1000, max_value=250000, value=25000, step=1000)

st.markdown("---")

if creds and creds.valid:
    # build service
    service = get_service_from_credentials(creds)
    st.info("Fetching site summaries from Google Search Console...")
    try:
        # generate_report returns a pandas.DataFrame or similar - the wrapper function should remain compatible
        df = generate_report(service=service, start_date=str(start_date), end_date=str(end_date), row_limit=int(row_limit))
        if df is not None:
            st.success("Report generated ✅")
            st.dataframe(df)
            csv = df.to_csv(index=False)
            st.download_button("Download CSV", csv, file_name="gsc_report.csv", mime="text/csv")
        else:
            st.warning("No data returned.")
    except Exception as e:
        st.error("Error while generating report:")
        st.exception(e)
else:
    st.info("Please sign in first using the link above.")

