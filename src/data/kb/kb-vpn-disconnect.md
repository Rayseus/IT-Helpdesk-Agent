---
id: kb-vpn-disconnect
title: VPN Frequent Disconnect Troubleshooting
category: vpn
tags: [vpn, disconnect, remote, connectivity]
last_updated: 2026-02-20
---

# VPN Frequent Disconnect Troubleshooting

## Common causes
- Unstable home Wi-Fi or switching networks
- Outdated VPN client (GlobalProtect < 6.2)
- Expired device certificate
- VPN gateway maintenance

## Steps
1. Update GlobalProtect to latest version (6.2+) from Software Center.
2. Reboot router and reconnect to stable Wi-Fi (avoid mobile hotspot if possible).
3. Open GlobalProtect → Settings → Clear config, then reconnect.
4. Check certificate: Keychain Access → search "Company VPN" — must not be expired.
5. If disconnects every 10–15 min, try wired connection to rule out Wi-Fi drops.
6. Confirm no other VPN clients are running (Cisco AnyConnect, etc.).

## During maintenance
- VPN gateway maintenance may cause brief disconnects every 10–15 minutes.
- Use web-only internal apps via Okta SSO where possible until the window ends.
- Check status page for ETA before opening a ticket.

## Escalate if
- Issue persists after client update, config clear, and certificate check.
- Disconnects continue when gateway health is healthy (not maintenance/outage).
