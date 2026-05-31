---
id: kb-snowflake-access
title: Snowflake Production Database Access
category: access
tags: [snowflake, database, production, access]
last_updated: 2026-01-10
---

# Snowflake Production Database Access

## Policy
Production Snowflake access is **never** self-service. Requires:
- Data Engineering or approved analyst role
- Manager approval
- Security review for write access

## Agent actions
- Explain approval workflow
- Generate escalation to Data Platform with required fields: business justification, data scope, manager name

## Dev/staging Snowflake
May be self-service for Data Engineering via `grant_snowflake_dev` policy.
