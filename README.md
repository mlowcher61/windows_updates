# Windows Server Patching & Posture Reporting via AAP

Automate Windows Server patching from **Ansible Automation Platform (AAP)** and produce a security-posture report that tells Windows administrators exactly where their fleet stands.

> Built for **AAP**, not ansible-core. Uses **certified** Red Hat content (`ansible.windows`, `ansible.platform`). Credentials live in AAP custom credential types — **no vaulted files** in git.

**[See an example report →](https://mlowcher61.github.io/windows_updates/example_report.html)**

[![Example posture report](docs/example_report.png)](https://mlowcher61.github.io/windows_updates/example_report.html)

---

## What this solves

Windows Update for Business reports (Microsoft's hosted reporting service) **only supports Windows 10/11 clients** — it does **not** cover Windows Server. Server admins are typically left stitching together WSUS reports, SCCM compliance views, or Azure Update Manager (Arc-only) to answer a simple question: *"What is the patch posture of my Windows Server fleet right now?"*

This repository delivers, end-to-end:

1. A scheduled, change-controlled **patch workflow** in AAP (scan → approval → install → reboot → verify)
2. A single **security-posture report** (HTML + CSV + email) that summarises the fleet against a weighted scoring model derived from Microsoft Learn guidance on patch compliance and the ASD Essential Eight ISM controls 1694 / 1877

## Architecture (at a glance)

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        AAP Workflow Template                              │
│                                                                          │
│  ┌─────────┐    ┌──────────┐    ┌─────────┐    ┌─────────┐    ┌────────┐ │
│  │  Scan   │──▶ │ Approval │──▶ │ Install │──▶ │ Verify  │──▶ │ Report │ │
│  │   JT    │    │  (prod)  │    │   JT    │    │ (in JT) │    │   JT   │ │
│  └─────────┘    └──────────┘    └─────────┘    └─────────┘    └────────┘ │
│       │                              │              │              │     │
│       ▼                              ▼              ▼              ▼     │
│   /tmp/patch_facts/<host>.scan.json + .install.json on AAP runner       │
│                                                          │              │
│                                                          ▼              │
│                                                  HTML + CSV artifact    │
│                                                  + email to admins      │
└──────────────────────────────────────────────────────────────────────────┘
```

## Prerequisites

| Component | Minimum | Notes |
| --- | --- | --- |
| Ansible Automation Platform | 2.4+ | Uses `ansible.platform` collection for config-as-code |
| Target Windows Server | 2016 / 2019 / 2022 / 2025 | 2012 R2 still works (ESU only — flagged in report) |
| WinRM | Listener on 5986 (HTTPS) | Kerberos preferred; NTLM supported |
| Execution Environment | Custom EE in `execution-environment/` | Includes `pywinrm`, `requests-kerberos`, `jmespath` |

## Quick start (demo — single host)

```bash
# 1. Install dependencies
ansible-galaxy collection install -r collections/requirements.yml

# 2. Edit the demo inventory with your test host
vi inventories/demo/hosts.yml

# 3. Set WinRM credentials in environment (demo only — production uses AAP credentials)
export ANSIBLE_USER='Administrator'
export ANSIBLE_PASSWORD='...'

# 4. Run the full cycle
ansible-playbook -i inventories/demo/hosts.yml playbooks/99_full_cycle.yml

# 5. Open the report
open reports/posture-report-*.html
```

## Production setup

### 1. Deploy AAP config-as-code

Run this from a job template in AAP with a **Red Hat Ansible Automation
Platform** credential attached. That credential injects `CONTROLLER_HOST`,
`CONTROLLER_USERNAME` and `CONTROLLER_PASSWORD` into the job environment, and
the `ansible.controller` modules read them automatically — so no hostname or
password is ever passed as an extra-var or stored in git.

To run it from a workstation instead, export the same variables yourself:

```bash
export CONTROLLER_HOST=aap.example.com
export CONTROLLER_USERNAME=admin
export CONTROLLER_PASSWORD=...        # or CONTROLLER_OAUTH_TOKEN
ansible-navigator run aap/deploy_aap.yml
```

This creates:
- 3 **custom credential types** (`windows_winrm_kerberos`, `wsus_source`, `smtp_relay`)
- 3 **job templates** (Scan, Install, Report)
- 1 **workflow template** with a conditional approval node
- 2 **notification templates** (success / failure email)
- 2 **schedules** (Patch Tuesday + 3 days dev, + 7 days prod)

### 2. Enter credentials in AAP

After `deploy_aap.yml` runs, open AAP → Resources → Credentials. Three credentials need values filled in:
- `cred_winrm_prod` — Windows service account
- `cred_wsus_corporate` (optional) — leave empty to use Microsoft Update
- `cred_smtp_relay` — relay used for the report email

### 3. Adapt the inventory

Edit `inventories/production/hosts.yml` to list your hosts. Three groups drive behaviour:

| Group | Behaviour |
| --- | --- |
| `prod` | Approval gate enforced, install Security + Critical only |
| `dev` | No approval, install all update categories |
| `sensitive` | Scan-only — never installs, only reports |

### 4. First run

Launch the workflow template `Windows Patch Cycle` from AAP. On prod hosts you will be prompted for approval before installation proceeds. The report appears as a job artifact and is emailed to the distribution list.

## Reading the report

A live example is published here: **[mlowcher61.github.io/windows_updates/example_report.html](https://mlowcher61.github.io/windows_updates/example_report.html)**

The HTML report has four sections:

1. **Fleet grade card** — A–F grade with overall score out of 100
2. **Posture breakdown** — six metrics as progress bars (security currency, ISM SLA compliance, reboot hygiene, OS lifecycle, recency, failure rate)
3. **Top 5 risks** — the most urgent items, ranked
4. **Per-host detail** — collapsible blocks with missing KBs, lifecycle status, errors

See [docs/REPORT_METRICS.md](docs/REPORT_METRICS.md) for the exact scoring formula and Microsoft Learn references.

## Customization

| Want to change… | Edit this file |
| --- | --- |
| Posture grade weights | `roles/windows_patch_report/defaults/main.yml` |
| ISM compliance thresholds (48hr / 14d) | `roles/windows_patch_report/defaults/main.yml` |
| Update categories per environment | `inventories/production/group_vars/<group>.yml` |
| OS lifecycle dates | `files/os_lifecycle.yml` |
| Install batch size (serial %) | `inventories/production/group_vars/<group>.yml` |
| Report email recipients | Survey on the Report job template in AAP |

## Extending

- **ServiceNow integration** — push report records into CMDB / change tickets. See [docs/EXTENDING.md](docs/EXTENDING.md).
- **Promotion to a collection** — `galaxy.yml` already in place. See [docs/EXTENDING.md](docs/EXTENDING.md).
- **Molecule tests** — `tests/` skeleton in place; full implementation on the roadmap.

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| WinRM connection fails | Kerberos ticket / SPN missing | Verify `setspn -L <service-account>` includes HTTP/host |
| `win_updates` hangs | Windows Update service paused | `Get-Service wuauserv` on host; restart if Stopped |
| Report shows 0 hosts | Patch-facts dir not preserved between JTs | Confirm AAP EE writable artifact dir is consistent across JTs |
| ISM SLA always failing | First run has no history | Posture computes from current scan only — accurate after 2+ cycles |
| Approval node not appearing | `require_approval` var = false at workflow level | Set on prod group_vars or at launch time |

## License

MIT. See `LICENSE`.

## Maintainer

Mark Lowcher · mlowcher@redhat.com · https://github.com/mlowcher61
