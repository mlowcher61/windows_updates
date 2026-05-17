# CLAUDE.md — Agent Guidance for the windows_updates repo

This file gives Claude (or any agent) project-specific context when working in
this repository.

## What this repo is

An AAP-driven Windows Server patching solution with security-posture reporting.
Three roles (scan / install / report), four playbooks, and AAP config-as-code
under `aap/` using the `ansible.platform` collection (not `ansible.controller`).

## Local conventions

- Always use `ansible.platform` for AAP CaC, never `ansible.controller`
- Use **certified** collections (`ansible.windows`) over community where both exist
- Credentials live in AAP custom credential types — never write vaulted files
  into git
- `files/os_lifecycle.yml` is the canonical OS lifecycle data; extend by
  appending entries (do not edit the filter plugin to add OS coverage)
- Posture weights and ISM thresholds live in
  `roles/windows_patch_report/defaults/main.yml` — customers tune those, not the
  plugin

## Known TODOs

- `filter_plugins/posture.py :: top_risks_ranking()` is a placeholder.
  Replace with the team's preferred ranking strategy. See docs/REPORT_METRICS.md.

## When making changes

1. If adding a new metric, update `roles/windows_patch_report/defaults/main.yml`
   (weights and thresholds), the filter plugin, AND docs/REPORT_METRICS.md
2. If adding a new credential type, register it in `aap/00_credential_types.yml`
   and add a shell credential in `aap/01_credentials.yml`
3. Re-run `aap/deploy_aap.yml` after AAP CaC changes — it's idempotent
