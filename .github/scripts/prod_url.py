"""Resolve a deployment's production alias through the Vercel REST API.

Used only when the PROD_API_URL / PROD_WEB_URL repository variables are unset.
Exits non-zero with a clear message when no production alias is found.
"""

import json
import os
import sys
import urllib.request

url = sys.argv[1]
host = url.split("://", 1)[-1].rstrip("/")
request = urllib.request.Request(
    f"https://api.vercel.com/v13/deployments/{host}?teamId={os.environ['VERCEL_ORG_ID']}",
    headers={"Authorization": f"Bearer {os.environ['VERCEL_TOKEN']}"},
)
with urllib.request.urlopen(request, timeout=30) as response:
    payload = json.load(response)

# Branch aliases look like <project>-git-<branch>-<team>.vercel.app. The
# production alias is the short one, and custom domains are left to the variable.
aliases = [
    alias
    for alias in payload.get("alias", [])
    if alias.endswith(".vercel.app") and "-git-" not in alias
]
if not aliases:
    sys.exit(f"No production alias found for {host}. Set PROD_API_URL / PROD_WEB_URL.")

print(f"https://{min(aliases, key=len)}")
