# Extending This Solution

## ServiceNow integration

Add a post-report task in `roles/windows_patch_report/tasks/main.yml` (or a new
role `windows_patch_servicenow`) that posts a record to ServiceNow per host
using `servicenow.itsm.incident` or `servicenow.itsm.api`. Use a new custom
credential type `servicenow_api` following the same pattern as `smtp_relay` in
`aap/00_credential_types.yml`.

## Promotion to a collection (Approach B)

The repository is already collection-shaped. To publish as
`mlowcher61.windows_patching`:

1. Fill out `galaxy.yml` (already in repo root) with final version
2. Move `filter_plugins/posture.py` → `plugins/filter/posture.py`
3. `ansible-galaxy collection build`
4. `ansible-galaxy collection publish ./mlowcher61-windows_patching-0.1.0.tar.gz`

The roles, playbooks, and AAP CaC files do not move — only the filter plugin
path changes.

## Custom report sections

The HTML template (`templates/report.html.j2`) is intentionally simple
(single file, inline CSS). To add a section:

1. Add data computation to the filter plugin (a new filter)
2. Call the new filter in `roles/windows_patch_report/tasks/main.yml` and store
   into a set_fact
3. Add a new `<div class="card">` block in the HTML template that iterates the
   new fact
