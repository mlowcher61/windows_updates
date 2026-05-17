# Report Metrics Reference

This document defines every metric on the posture report, links each one back to
Microsoft Learn / ASD ISM guidance, and shows the scoring formula.

## Why Windows Server reporting is its own problem

Microsoft's hosted **Windows Update for Business reports** product only supports
Windows 10/11 *clients* — it does not surface Windows Server data
(https://learn.microsoft.com/windows/deployment/update/wufb-reports-prerequisites).
For server fleets, administrators have historically relied on WSUS, SCCM,
Azure Update Manager (Arc-enabled only), or hand-rolled PowerShell.
This solution provides a vendor-neutral alternative driven from AAP.

## Posture grade formula

Each host receives a 0–100 score. The fleet score is the mean of host scores.

| Component | Weight | What it measures | Source |
| --- | ---:| --- | --- |
| security_currency | 30 | % of missing updates that are NOT critical/security | WUfB "missing security updates" headline metric |
| ism_sla            | 20 | Hours since last install vs ISM target (48h critical / 14d std) | ASD ISM 1694 / 1877 |
| reboot_hygiene     | 15 | No pending reboot at scan time | Operational hygiene |
| lifecycle          | 15 | OS in support, near EoS, or past EoS | Microsoft Product Lifecycle |
| patch_recency      | 10 | Days since last successful patch ≤ 35 (default) | Stale-host indicator |
| failure_rate       | 10 | No failed updates during last install | Direct troubleshooting signal |

Grade mapping: **A** ≥ 90 · **B** ≥ 80 · **C** ≥ 70 · **D** ≥ 60 · **F** < 60.

Weights live in `roles/windows_patch_report/defaults/main.yml` (`posture_weights`)
and must sum to 100. Thresholds (`posture_thresholds`) are tuned in the same file.

## Per-metric definitions

### security_currency
`100` when no updates are missing.
`80` when missing updates exist but none are Security or Critical.
Otherwise `max(0, 100 - 20 * count_of_missing_critical_or_security)`.

### ism_sla
Hours since `install_time` for this cycle:
- ≤ 48h → 100
- ≤ 14d → 75
- thereafter → linear penalty 5 pts per day beyond 14

### reboot_hygiene
0 if `pending_reboot_before_scan` is true, else 100.

### lifecycle
Compares today's date against `files/os_lifecycle.yml`:
- `today >= extended_end` → `past_eos` (score 0)
- `today + 365d >= extended_end` → `near_eos` (score 60)
- supported → 100
- unknown OS → 50

### patch_recency
Days since `last_successful_patch`:
- ≤ 35 days → 100
- otherwise `max(0, 100 - 2 * (days_over_target))`

### failure_rate
0 when any update failed or the install raised an error, else 100.

## Top Risks ranking

`filter_plugins/posture.py :: top_risks_ranking()` selects the top N hosts to surface
in the report's Top Risks section. **This function is marked as a user contribution
point** — multiple valid ranking strategies exist:

| Strategy | When to use |
| --- | --- |
| Pure grade | Default; simple A/B/C/D/F sort |
| Lifecycle-first | When compliance/audit drives priorities |
| Severity-weighted | When CVE response is the operational focus |
| Composite | Custom blend reflecting your team's triage rhythm |

See the TODO block at the bottom of `filter_plugins/posture.py`.

## Microsoft Learn references used in this report design

- Windows Update for Business reports overview: https://learn.microsoft.com/windows/deployment/update/wufb-reports-overview
- Microsoft 365 admin center software updates page: https://learn.microsoft.com/windows/deployment/update/wufb-reports-admin-center
- Microsoft Product Lifecycle: https://learn.microsoft.com/lifecycle/products/
- Azure Update Manager unified patch compliance dashboard: https://learn.microsoft.com/azure/azure-arc/servers/cloud-native/patch-management#unified-patch-compliance-dashboard
- ASD Essential Eight — patch operating systems: https://learn.microsoft.com/compliance/anz/e8-patch-os
- MCSB PV-6 (rapid vulnerability remediation): https://learn.microsoft.com/security/benchmark/azure/mcsb-v2-posture-vulnerability-management
