---
id: kb-okta-mfa-unlock
title: Okta MFA Device Unlock
category: password
tags: [okta, mfa, locked, unlock]
last_updated: 2026-03-15
---

# Okta MFA Device Unlock

## Symptoms
- "Too many failed attempts" after password reset
- MFA push not received
- Account status: locked

## Agent can guide (self-service)
1. Wait 15 minutes for automatic lockout expiry.
2. Try Okta Verify on mobile — tap **Reset** if prompted.
3. Use backup MFA factor if enrolled.

## Requires IT (escalate)
- MFA device lost or not enrolled → IT must reset MFA binding.
- Account locked with `lock_reason: too_many_mfa_attempts` → IT Helpdesk unlock.
