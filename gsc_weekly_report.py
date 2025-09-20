# gsc_weekly_report.py
from typing import Optional
import pandas as pd

# google client libraries
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

# Search Console scope is webmasters.readonly (app.py ensures credential contains required scope)


def get_service_from_credentials(credentials: Credentials):
    """
    Build and return a Search Console (webmasters) service instance
    using googleapiclient.discovery.build. This expects google-api-python-client.
    """
    # webmasters api name is 'webmasters' and version is 'v3'
    service = build("webmasters", "v3", credentials=credentials, cache_discovery=False)
    return service


def generate_report(service, start_date: str, end_date: str, row_limit: int = 25000) -> Optional[pd.DataFrame]:
    """
    A simple multi-site report generator.
    - Lists sites the authenticated account has access to
    - For each site requests a searchAnalytics query for the given dates (top queries)
    - Returns concatenated DataFrame with site column + query stats.

    NOTE: This is intentionally conservative and uses only 'query' dimension and aggregated metrics.
    You can extend it to pages, devices, country, etc.
    """
    # list sites
    sites_resp = service.sites().list().execute()
    sites = []
    for s in sites_resp.get("siteEntry", []):
        site_url = s.get("siteUrl")
        # filter verified/owner? include all accessible
        sites.append(site_url)

    frames = []
    for site in sites:
        try:
            # build request body for searchAnalytics.query
            body = {
                "startDate": start_date,
                "endDate": end_date,
                "dimensions": ["query"],
                "rowLimit": row_limit,
            }
            resp = service.searchanalytics().query(siteUrl=site, body=body).execute()
            rows = resp.get("rows", [])
            if not rows:
                continue
            recs = []
            for r in rows:
                keys = r.get("keys", [])
                query = keys[0] if keys else ""
                clicks = r.get("clicks", 0)
                impressions = r.get("impressions", 0)
                ctr = r.get("ctr", 0)
                position = r.get("position", 0)
                recs.append(
                    {
                        "site": site,
                        "query": query,
                        "clicks": clicks,
                        "impressions": impressions,
                        "ctr": ctr,
                        "position": position,
                    }
                )
            if recs:
                df_site = pd.DataFrame.from_records(recs)
                frames.append(df_site)
        except Exception:
            # skip site on any error (e.g., insufficient permission or API error)
            continue

    if frames:
        df = pd.concat(frames, ignore_index=True)
        # basic sorting & trimming
        df = df.sort_values(["site", "clicks"], ascending=[True, False])
        return df
    return pd.DataFrame(columns=["site", "query", "clicks", "impressions", "ctr", "position"])
