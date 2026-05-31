---
id: kb-okta-reset
title: Okta Password Reset Runbook
category: password
tags: [okta, password, reset, login]
last_updated: 2026-04-01
---

# Okta Password Reset Runbook

## When to use
Employee cannot log into Okta after a password reset or forgot their password.

## Self-service steps
1. Go to https://company.okta.com and click **Forgot Password**.
2. Enter your `@company.com` email and complete MFA on your registered device.
3. Check email for reset link (expires in 30 minutes).
4. Set a new password meeting complexity requirements (12+ chars, upper, lower, number, symbol).
5. Clear browser cache or use incognito before retrying login.

## If self-service fails
- Verify MFA device is enrolled and not locked.
- Contact IT if account shows **locked** after too many attempts.
- If password reset was already attempted: clear browser cache, try incognito, verify MFA app, wait 15 min for lockout expiry.
