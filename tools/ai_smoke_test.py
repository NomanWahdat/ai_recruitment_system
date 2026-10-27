"""Explicit local smoke test with a real document. Run the browser E2E suite for the complete flow."""

import os
import requests

API = os.getenv("DEMO_API", "http://127.0.0.1:8000/api")
session = requests.Session()
csrf = session.get(API + "/auth/csrf/", timeout=10).json()["csrfToken"]
response = session.post(
    API + "/auth/login/",
    json={
        "username": os.getenv("DEMO_USERNAME", "portfolio_demo"),
        "password": os.environ["DEMO_PASSWORD"],
    },
    headers={"X-CSRFToken": csrf},
    timeout=10,
)
response.raise_for_status()
session.headers["X-CSRFToken"] = response.json()["csrfToken"]
response = session.get(API + "/candidates/", timeout=10)
response.raise_for_status()
print("Authenticated candidates:", response.json()["count"])
print(
    "Use tools/browser_e2e.cjs for upload, correction, matching, human review and failure checks."
)
