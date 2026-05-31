---
id: kb-grafana-access
title: Grafana Dashboard Access (Read-Only)
category: access
tags: [grafana, dashboard, access, read-only]
last_updated: 2026-01-10
---

# Grafana Dashboard Access (Read-Only)

## Self-service eligible
Employees in Engineering, Data Engineering, or SRE may request **Grafana read-only** access.

## Steps (Agent can simulate grant)
1. Confirm employee department and role.
2. Verify policy allows `grant_grafana_readonly`.
3. Add user to Okta group `grafana-viewers`.
4. Access available at https://grafana.internal.company.com within 15 minutes.

## Not self-service
- Grafana admin or edit permissions require manager approval.
