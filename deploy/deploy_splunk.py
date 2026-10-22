#!/usr/bin/env python3
"""
MilliSec Blue Team - SIEM Rule Deployment (GitHub -> Splunk)
------------------------------------------------------------
Fetches the version-controlled detection rules from GitHub and deploys them to
Splunk as scheduled saved searches (alerts) via the Splunk REST API.

Design:
  * Rules live on GitHub (splunk/splunk_rules.yml) as the single source of truth.
  * This script pulls that YAML and creates/updates each rule in Splunk.
  * To change a rule, edit it on GitHub and re-run this script; Splunk updates.

Usage        : python3 deploy_splunk.py
Dependencies : pip3 install requests pyyaml
"""
import sys
from datetime import datetime

import yaml
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ============================ CONFIG ============================
# Raw URL of the rule file on GitHub (update the branch if not 'main').
GITHUB_RAW = "https://raw.githubusercontent.com/itsnazrinn/siem-rules/main/splunk/splunk_rules.yml"

# Splunk REST API (management port 8089, NOT the web port 8000).
SPLUNK_URL  = "https://52.204.109.217:8089"
SPLUNK_USER = "blueteam"
SPLUNK_PASS = "CHANGE_ME_SPLUNK_PASSWORD"
SPLUNK_APP  = "search"

# Email target for triggered alerts (optional).
ALERT_EMAIL = "splunk-alert@milli.lol"
# ================================================================

SEVERITY_MAP = {"low": "2", "medium": "3", "high": "4", "critical": "5"}


def log(msg):
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def fetch_rules():
    """Download and parse the rule file from GitHub."""
    resp = requests.get(GITHUB_RAW, timeout=30)
    resp.raise_for_status()
    rules = yaml.safe_load(resp.text).get("rules", [])
    log(f"Fetched {len(rules)} rule(s) from GitHub.")
    return rules


def deploy_rule(rule):
    """Create or update a single rule in Splunk as a scheduled alert."""
    name = rule["name"]
    severity = rule.get("severity", "medium")

    base = f"{SPLUNK_URL}/servicesNS/{SPLUNK_USER}/{SPLUNK_APP}/saved/searches"
    auth = (SPLUNK_USER, SPLUNK_PASS)

    payload = {
        "name": name,
        "search": rule["search"].strip(),
        "description": rule.get("description", ""),
        "is_scheduled": "1",
        "cron_schedule": rule.get("cron", "*/5 * * * *"),
        "dispatch.earliest_time": "-5m",
        "dispatch.latest_time": "now",
        "alert_type": "number of events",
        "alert_comparator": "greater than",
        "alert_threshold": "0",
        "alert.severity": SEVERITY_MAP.get(severity, "3"),
        "actions": "email",
        "action.email.to": ALERT_EMAIL,
        "action.email.subject": f"[{severity.upper()}] SIEM Alert: {name}",
    }

    # If the rule already exists -> update it; otherwise -> create it.
    quoted = requests.utils.quote(name)
    exists = requests.get(f"{base}/{quoted}", auth=auth,
                          params={"output_mode": "json"}, verify=False)

    if exists.status_code == 200:
        update = {k: v for k, v in payload.items() if k != "name"}
        resp = requests.post(f"{base}/{quoted}", auth=auth, data=update, verify=False)
        action = "updated"
    else:
        resp = requests.post(base, auth=auth, data=payload, verify=False)
        action = "created"

    if resp.status_code in (200, 201):
        log(f"  [OK]   {severity.upper():8} {name}  ->  {action}")
        return True

    log(f"  [FAIL] {resp.status_code}  {name}: {resp.text[:150]}")
    return False


def main():
    log("===== Deploying SIEM rules: GitHub -> Splunk =====")
    rules = fetch_rules()

    deployed = sum(deploy_rule(rule) for rule in rules)

    log(f"===== Done: {deployed}/{len(rules)} rule(s) deployed to Splunk =====")
    if deployed < len(rules):
        sys.exit(1)


if __name__ == "__main__":
    main()
