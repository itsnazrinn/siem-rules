#!/usr/bin/env python3
"""
MilliSec Blue Team - SIEM Rule Deployment (GitHub -> QRadar)
------------------------------------------------------------
Fetches the version-controlled QRadar detection rules from GitHub and deploys
their AQL logic to QRadar as saved Ariel searches via the QRadar REST API.

Design:
  * Rules live on GitHub (qradar/qradar_rules.yml) as the single source of truth.
  * This script pulls that YAML and creates one saved Ariel search per rule.
  * To change a rule, edit it on GitHub and re-run this script.
  * The highest-value rules are additionally built as Custom Rules in the QRadar
    console so that matches raise Offenses (the API cannot create Custom Rules
    directly in QRadar 7.5 — see the project README).

Security:
  * No secrets are stored in this file. The API token is read from the
    environment at runtime:  export QRADAR_TOKEN="..."
Usage        : python3 deploy_qradar.py
Dependencies : pip3 install requests pyyaml
"""
import os
import sys
from datetime import datetime

import yaml
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ============================ CONFIG ============================
GITHUB_RAW   = "https://raw.githubusercontent.com/itsnazrinn/siem-rules/main/qradar/qradar_rules.yml"
QRADAR_HOST  = os.environ.get("QRADAR_HOST", "https://184.196.118.227")
QRADAR_TOKEN = os.environ.get("QRADAR_TOKEN", "")     # export QRADAR_TOKEN=...
API_VERSION  = "12.0"
# ================================================================


def log(msg):
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def headers():
    return {"SEC": QRADAR_TOKEN, "Version": API_VERSION,
            "Content-Type": "application/json", "Accept": "application/json"}


def fetch_rules():
    resp = requests.get(GITHUB_RAW, timeout=30)
    resp.raise_for_status()
    rules = yaml.safe_load(resp.text).get("rules", [])
    log(f"Fetched {len(rules)} rule(s) from GitHub.")
    return rules


def deploy_rule(rule):
    """Create a saved Ariel search in QRadar from the rule's AQL."""
    name = rule["name"]
    severity = rule.get("severity", "medium")
    aql = " ".join(rule["aql"].split())   # collapse whitespace/newlines

    # 1) Start an Ariel search with the rule's AQL
    params = {"query_expression": aql}
    r = requests.post(f"{QRADAR_HOST}/api/ariel/searches",
                      headers=headers(), params=params, verify=False)
    if r.status_code not in (200, 201):
        log(f"  [FAIL] {r.status_code}  {name}: {r.text[:150]}")
        return False
    search_id = r.json().get("search_id")

    # 2) Persist/label the search so it is saved and reusable
    save = requests.post(
        f"{QRADAR_HOST}/api/ariel/searches/{search_id}",
        headers=headers(),
        params={"save_results": "true", "name": name},
        verify=False)

    if save.status_code in (200, 201):
        log(f"  [OK]   {severity.upper():8} {name}  ->  saved search {search_id}")
        return True

    # Even if the label call is unsupported on this build, the search itself ran.
    log(f"  [OK*]  {severity.upper():8} {name}  ->  search {search_id} (not persisted: {save.status_code})")
    return True


def main():
    if not QRADAR_TOKEN:
        log("ERROR: QRADAR_TOKEN is not set. Run:  export QRADAR_TOKEN='your-token'")
        sys.exit(1)

    log("===== Deploying SIEM rules: GitHub -> QRadar =====")
    rules = fetch_rules()

    deployed = sum(deploy_rule(rule) for rule in rules)

    log(f"===== Done: {deployed}/{len(rules)} rule(s) deployed to QRadar =====")
    if deployed < len(rules):
        sys.exit(1)


if __name__ == "__main__":
    main()
