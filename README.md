# MilliSec SIEM Detection Rules

Centralized, version-controlled detection rules for the MilliSec Blue Team SOC.

This repository is the **single source of truth** for all SIEM detection content.
Rules are authored and reviewed here on GitHub, then pushed to the SIEM platforms
(**Splunk** and **IBM QRadar**) through their REST APIs. Editing a rule and
re-running the deploy script applies the change to the SIEM automatically —
a GitOps workflow for detection engineering that gives us version history,
peer review, rollback, and repeatable, auditable deployments.

---

## Why rules live in GitHub (not only in the SIEM)

Writing rules directly inside a SIEM has no history, no review, and no easy way
to replicate them to a second platform. By keeping the detection logic in Git:

- Every change is tracked (who, when, why) through commit history.
- Rules can be reviewed before they reach production.
- The exact same source deploys to multiple SIEMs via each platform's API.
- A broken rule can be reverted to a previous commit instantly.

---

## Repository structure

```
siem-rules/
├── README.md                   # this document
├── splunk/
│   └── splunk_rules.yml        # 15 detection rules (OWASP Top 10 / web attacks)
├── qradar/
│   └── qradar_rules.yml        # 10 detection rules (Windows / Active Directory)
└── deploy/
    ├── deploy_splunk.py        # GitHub -> Splunk  REST API deployment
    └── deploy_qradar.py        # GitHub -> QRadar  REST API deployment
```

---

## Splunk rules (15)

**Data source:** `index=web_logs`, `sourcetype=millisec:nginx` (NGINX JSON access logs).
**Focus:** web application attacks, aligned to the OWASP Top 10.
Rules are deployed as scheduled alerts that run every 5 minutes and notify the SOC.

| #  | Rule                                   | OWASP | Severity |
|----|----------------------------------------|-------|----------|
| 1  | SQL Injection Attempt                  | A03   | High     |
| 2  | Cross-Site Scripting (XSS)             | A03   | High     |
| 3  | Path Traversal                         | A01   | High     |
| 4  | Command Injection                      | A03   | Critical |
| 5  | Known Scanner User-Agent               | —     | Medium   |
| 6  | Brute Force (401/403 burst)            | A07   | High     |
| 7  | Server Error Spike (HTTP 5xx)          | —     | Medium   |
| 8  | DoS Request Flood                      | —     | High     |
| 9  | Sensitive File Access (.env, .git)     | A05   | High     |
| 10 | SSRF                                   | A10   | High     |
| 11 | HTTP Method Abuse (PUT/DELETE/TRACE)   | —     | Medium   |
| 12 | Log4Shell / JNDI Injection             | A06   | Critical |
| 13 | WordPress Targeted Attack              | —     | Medium   |
| 14 | Admin Panel Enumeration                | —     | Medium   |
| 15 | Directory Brute Force (high 404 rate)  | —     | Medium   |

---

## QRadar rules (10)

**Data source:** Windows Domain Controller (DC01) via WinCollect + WindowsAuthServer
(log sources 262–264) and Sysmon.
**Focus:** Windows / Active Directory security monitoring.
Rule logic is written in **AQL** (Ariel Query Language) and deployed as saved
Ariel searches through the QRadar REST API.

| #  | Rule                                   | Windows Event ID   | Severity |
|----|----------------------------------------|--------------------|----------|
| 1  | New User Account Created               | 4720               | High     |
| 2  | User Added to Privileged Group         | 4728 / 4732 / 4756 | Critical |
| 3  | Brute Force (failed logon burst)       | 4625               | High     |
| 4  | Account Lockout                        | 4740               | Medium   |
| 5  | User Account Deleted                   | 4726               | High     |
| 6  | Special Privileges Assigned at Logon   | 4672               | Medium   |
| 7  | Security Audit Log Cleared             | 1102               | Critical |
| 8  | Password Reset by Another Account      | 4724               | Medium   |
| 9  | Disabled Account Re-Enabled            | 4722               | High     |
| 10 | Suspicious Process Creation (LOLBins)  | Sysmon 1           | High     |

---

## Deployment

```bash
pip3 install requests pyyaml

# ---- Splunk ----
export SPLUNK_USER="blueteam"
export SPLUNK_PASS="********"        # supplied at runtime, never committed
python3 deploy/deploy_splunk.py

# ---- QRadar ----
export QRADAR_TOKEN="********"       # supplied at runtime, never committed
python3 deploy/deploy_qradar.py
```

Each run is idempotent: existing rules are **updated**, new ones are **created**.
Change a rule in this repo, commit, re-run the script, and the SIEM is updated.

---

## QRadar Offenses (Custom Rules)

QRadar 7.5 does not allow Custom Rules to be created through the REST API, so the
AQL above is deployed as saved Ariel searches via the API (this satisfies the
required "rules stored in GitHub, pushed via API" workflow). To additionally
raise **Offenses**, the highest-value detections are also implemented as Custom
Rules in the QRadar console (Rule Wizard) using the same logic:

1. **New User Account Created** — Event ID 4720 → create Offense.
2. **User Added to Privileged Group** — Event ID 4728 / 4732 → create Offense.
3. **Security Audit Log Cleared** — Event ID 1102 → create Offense.

When an Offense is closed, two custom close reasons are recorded in addition to
the three QRadar defaults: **True-Positive** and **False-Positive**
(configured under Admin → Custom Offense Close Reasons).

---

## Alerting & response

- **Splunk** alerts email the SOC mailbox (`splunk-alert@milli.lol`) on a match.
- **QRadar** matches surface as Offenses for triage in the Offenses tab.
- High/Critical detections are intended to feed the ticketing system and SOAR
  playbooks for automated response.

---

## Design references

Detection logic is informed by the **OWASP Top 10** (web layer, Splunk) and by
**SIGMA** rule patterns for Windows/AD telemetry (QRadar). Rules are written to
be specific and low-noise rather than broad catch-alls.

---

## Security

No credentials are stored in this repository. All secrets — the Splunk password
and the QRadar API token — are provided at runtime through environment variables
and never written to disk or committed to Git.
