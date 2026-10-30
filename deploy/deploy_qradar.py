#!/usr/bin/env python3
"""
MilliSec Blue Team - QRadar Rule Deployment (GitHub -> QRadar)   [v2: extension import]
---------------------------------------------------------------------------------------
Step 2 of the GitOps flow for QRadar.

Takes the version-controlled extension zip (qradar/rules_extension.zip) that
holds the 10 Custom Rules and pushes it to QRadar through the REST API:
    1. uploads the zip          POST /config/extension_management/extensions
    2. installs with overwrite  POST /config/extension_management/extensions/{id}
                                       ?action_type=INSTALL&overwrite=true
    3. waits until the install task reports INSTALLED/COMPLETED

Because these are real Custom Rules (not saved searches), installing them makes
QRadar raise Offenses on a match. overwrite=true means editing a rule in GitHub
and re-running this script UPDATES the rule in QRadar (the GitOps update flow).

Security:
  export QRADAR_HOST="10.0.0.5"
  export QRADAR_TOKEN="xxxxxxxx-...."     # supplied at runtime, never committed

Usage       : python3 deploy_qradar.py
Dependencies: pip3 install requests
"""

import os
import sys
import time
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HOST  = os.environ.get("QRADAR_HOST")
TOKEN = os.environ.get("QRADAR_TOKEN")
API_V = "17.0"
ZIP   = os.path.join(os.path.dirname(__file__), "..", "qradar", "rules_extension.zip")

if not HOST or not TOKEN:
    sys.exit("ERROR: set QRADAR_HOST and QRADAR_TOKEN environment variables first.")
if not os.path.exists(ZIP):
    sys.exit(f"ERROR: {ZIP} not found. Run export_qradar.py first (or git pull).")

BASE = f"https://{HOST}/api"
HEAD = {"SEC": TOKEN, "Version": API_V, "Accept": "application/json"}


def log(msg):
    print(f"[deploy] {msg}", flush=True)


def upload():
    log("uploading extension zip ...")
    with open(ZIP, "rb") as f:
        files = {"file": ("rules_extension.zip", f, "application/zip")}
        r = requests.post(f"{BASE}/config/extension_management/extensions",
                          headers=HEAD, files=files, verify=False, timeout=180)
    # 409/22613 = same hub_id+version already uploaded; reuse the existing one
    if r.status_code == 409:
        log("zip already uploaded; locating existing extension id ...")
        return find_existing()
    r.raise_for_status()
    ext_id = r.json()["id"]
    log(f"uploaded: extension id={ext_id}")
    return ext_id


def find_existing():
    r = requests.get(f"{BASE}/config/extension_management/extensions",
                     headers={**HEAD, "fields": "id,name,status"},
                     verify=False, timeout=60)
    r.raise_for_status()
    exts = r.json()
    if not exts:
        sys.exit("ERROR: upload said duplicate but no extensions listed.")
    ext = sorted(exts, key=lambda e: e["id"])[-1]        # newest
    log(f"using extension id={ext['id']} ({ext.get('status')})")
    return ext["id"]


def install(ext_id):
    log(f"installing extension id={ext_id} with overwrite=true ...")
    r = requests.post(
        f"{BASE}/config/extension_management/extensions/{ext_id}",
        headers=HEAD,
        params={"action_type": "INSTALL", "overwrite": "true"},
        verify=False, timeout=120)
    r.raise_for_status()                                  # 202 accepted
    status_id = r.json()["status_id"]
    log(f"install task started: status_id={status_id}")
    return status_id


def wait_for(status_id):
    url = f"{BASE}/config/extension_management/extensions_task_status/{status_id}"
    while True:
        r = requests.get(url, headers=HEAD, verify=False, timeout=60)
        r.raise_for_status()
        status = r.json().get("status")
        log(f"  status: {status}")
        if status in ("COMPLETED", "INSTALLED"):
            return
        if status in ("FAILED", "INSTALL_FAILED", "CANCELLED"):
            sys.exit(f"ERROR: install ended with status {status} -- check QRadar preview/logs.")
        time.sleep(4)


def main():
    log("===== Deploying QRadar rules: GitHub -> QRadar (extension import) =====")
    ext_id = upload()
    status_id = install(ext_id)
    wait_for(status_id)
    log("===== Done. Rules are live. Deploy Changes in the console if prompted. =====")


if __name__ == "__main__":
    main()
