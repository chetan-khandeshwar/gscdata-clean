# oauth_test.py
from gsc_weekly_report import _get_service
creds_path = r"E:\CT-GSC-Weekly-Notification\GSC-Report-App\client_secret.json"
svc = _get_service(creds_path)
print("Service created:", bool(svc))