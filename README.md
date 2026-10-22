# MilliSec SIEM Detection Rules

Version-controlled detection rules for the MilliSec Blue Team SOC.

Rules are maintained here on GitHub as the single source of truth and pushed to
the SIEM platforms (Splunk and QRadar) through their REST APIs. To change a rule,
edit it in this repository and re-run the relevant deploy script — the change is
applied to the SIEM automatically. This gives us version history, peer review,
and repeatable, auditable deployments.

## Repository structure

```
siem-rules/
├── splunk/
│   └── splunk_rules.yml        # 15 detection rules (OWASP Top 10 + web attacks)
├── qradar/
│   └── qradar_rules.yml        # 10 QRadar offense rules (coming next)
└── deploy/
    ├── deploy_splunk.py        # GitHub -> Splunk REST API deployment
    └── deploy_qradar.py        # GitHub -> QRadar REST API deployment (coming next)
```

## Splunk rules (15)

Source: `index=web_logs`, `sourcetype=millisec:nginx` (NGINX JSON access logs).

| # | Rule | OWASP | Severity |
|---|------|-------|----------|
| 1 | SQL Injection Attempt | A03 | High |
| 2 | Cross-Site Scripting (XSS) | A03 | High |
| 3 | Path Traversal | A01 | High |
| 4 | Command Injection | A03 | Critical |
| 5 | Known Scanner User-Agent | - | Medium |
| 6 | Brute Force (401/403 burst) | A07 | High |
| 7 | Server Error Spike (5xx) | - | Medium |
| 8 | DoS Request Flood | - | High |
| 9 | Sensitive File Access | A05 | High |
| 10 | SSRF | A10 | High |
| 11 | HTTP Method Abuse | - | Medium |
| 12 | Log4Shell / JNDI | A06 | Critical |
| 13 | WordPress Attack | - | Medium |
| 14 | Admin Panel Enumeration | - | Medium |
| 15 | Directory Brute Force (404 rate) | - | Medium |

## Deployment

```bash
pip3 install requests pyyaml
python3 deploy/deploy_splunk.py
```

Each rule is created or updated in Splunk as a scheduled alert that runs every
five minutes and notifies the SOC on a match.
