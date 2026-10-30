#!/usr/bin/env python3
import os, sys, time, yaml, requests, urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
HOST  = os.environ.get("QRADAR_HOST")
TOKEN = os.environ.get("QRADAR_TOKEN")
API_V = "17.0"
RULES_YML = os.path.join(os.path.dirname(__file__), "..", "qradar", "qradar_rules.yml")
OUT_ZIP   = os.path.join(os.path.dirname(__file__), "..", "qradar", "rules_extension.zip")
if not HOST or not TOKEN:
    sys.exit("ERROR: set QRADAR_HOST and QRADAR_TOKEN first.")
BASE = f"https://{HOST}/api"
HEAD = {"SEC": TOKEN, "Version": API_V, "Accept": "application/json"}
def log(m): print(f"[export] {m}", flush=True)
def load_rule_names():
    with open(RULES_YML, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    names = [r["name"] for r in data.get("rules", []) if r.get("name")]
    if not names: sys.exit("ERROR: no rule names in yml")
    return names
def find_rule_ids(names):
    r = requests.get(f"{BASE}/analytics/rules", headers={**HEAD, "fields": "id,name"}, verify=False, timeout=60)
    r.raise_for_status()
    live = {x["name"]: x["id"] for x in r.json()}
    ids, missing = [], []
    for n in names:
        if n in live:
            ids.append(str(live[n])); log(f"  found id={live[n]} {n}")
        else:
            missing.append(n); log(f"  MISSING -> {n}")
    if missing: sys.exit(f"ERROR: {len(missing)} rule(s) not found. Fix names, re-run.")
    return ids
def start_export(ids):
    body = {"export_contents": [{"content_item_ids": ids, "content_type": "CUSTOM_RULES", "related_content": [{"content_type": "FGROUP_LINKS"}]}]}
    r = requests.post(f"{BASE}/config/extension_management/extension_export_tasks", headers={**HEAD, "Content-Type": "application/json"}, json=body, verify=False, timeout=60)
    r.raise_for_status()
    tid = r.json()["task_id"]; log(f"export task={tid}"); return tid
def wait_for(tid):
    url = f"{BASE}/config/extension_management/extensions_task_status/{tid}"
    while True:
        r = requests.get(url, headers=HEAD, verify=False, timeout=60); r.raise_for_status()
        s = r.json().get("status"); log(f"  status: {s}")
        if s == "COMPLETED": return
        if s in ("FAILED", "CANCELLED"): sys.exit(f"ERROR: export {s}")
        time.sleep(3)
def download(tid):
    url = f"{BASE}/config/extension_management/extension_export_tasks/{tid}/extension_export"
    r = requests.get(url, headers={**HEAD, "Accept": "application/zip"}, verify=False, timeout=120)
    r.raise_for_status()
    os.makedirs(os.path.dirname(OUT_ZIP), exist_ok=True)
    with open(OUT_ZIP, "wb") as f: f.write(r.content)
    log(f"saved -> {os.path.normpath(OUT_ZIP)} ({len(r.content)} bytes)")
def main():
    log("===== Exporting QRadar Custom Rules -> extension zip =====")
    names = load_rule_names(); log(f"rules expected: {len(names)}")
    ids = find_rule_ids(names)
    tid = start_export(ids); wait_for(tid); download(tid)
    log("===== Done. Commit qradar/rules_extension.zip to GitHub. =====")
if __name__ == "__main__":
    main()
