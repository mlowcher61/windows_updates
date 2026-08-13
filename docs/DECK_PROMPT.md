# Slide deck prompt

A ready-to-use prompt for generating a customer-facing PowerPoint about this
solution. Written for Claude Cowork, but it is self-contained and works with
any assistant that can produce a `.pptx`.

It deliberately carries every fact the deck needs inline, so the assistant does
not need access to this repository. **If you change the solution, update the
facts below** — a stale prompt produces a confidently wrong deck.

Copy everything inside the fence:

```markdown
Create a 7-slide PowerPoint (.pptx, 16:9) explaining an Ansible Automation
Platform solution I built. I'm an Ansible solution architect at Red Hat and
I'll present this to a customer's Windows server and platform teams.

Everything factual you need is below — do not invent statistics, customer
names, cost savings, or time-to-value figures. If a slide feels thin without
a number, use a qualitative statement instead.

## The solution

Repo: github.com/mlowcher61/windows_updates
Example output report: https://mlowcher61.github.io/windows_updates/example_report.html

**Problem it solves.** Microsoft's Windows Update for Business reports only
covers Windows 10/11 *clients* — it does not cover Windows Server. Server
admins stitch together WSUS reports, SCCM compliance views, or Azure Update
Manager (Arc-only) to answer "what is the patch posture of my Windows Server
fleet right now?" There is no single answer today.

**What it delivers.** Two things, end to end:
1. A scheduled, change-controlled patch workflow in AAP
2. A single security-posture report (HTML + CSV + email) grading the fleet

**Workflow.** Scan → Approval gate (prod only) → Install → Verify → Report.
Each stage is an AAP job template; the whole thing is one workflow template.
Scan and install write JSON facts per host that the report job consumes.

**Inventory tiers drive behaviour** — this is the safety model:
- `prod` — approval gate enforced, installs Security + Critical updates only
- `dev` — no approval, installs all update categories
- `sensitive` — scan-only, never installs, reports only

**Scheduling.** Two AAP schedules: dev runs the third Friday of each month,
prod runs the third Tuesday, which is always exactly Patch Tuesday + 7 days.
Dev soaks before prod.

**The posture report.** A weighted score out of 100 mapped to an A–F fleet
grade, built from six metrics (weights shown):
- Security currency (30) — ratio of missing security/critical KBs
- ISM SLA compliance (20) — mean time to patch vs target
- Reboot hygiene (15) — no pending reboots
- OS lifecycle (15) — OS still in support
- Patch recency (10) — last patch within 35 days
- Failure rate (10) — no failed updates

Thresholds derive from the ASD Essential Eight ISM controls 1694 and 1877:
48 hours for critical/actively-exploited, 14 days for standard updates.
Microsoft Learn product-lifecycle guidance drives the OS lifecycle metric.
Report sections: fleet grade card, the six metrics as bars, top risks, and
collapsible per-host detail with missing KBs and errors.

**Enterprise plumbing.**
- Certified Red Hat content only: `ansible.windows`, `ansible.controller`
- Credentials live in AAP custom credential types (WinRM/Kerberos, WSUS
  source, SMTP relay) — no vaulted secrets in git
- Entire AAP footprint is config-as-code: one idempotent playbook creates 3
  custom credential types, 4 credentials, 3 job templates, 1 workflow with
  the conditional approval node, 2 email notification templates, 2 schedules
- Custom execution environment (pywinrm, requests-kerberos, jmespath)
- Targets Windows Server 2016/2019/2022/2025; 2012 R2 works but is flagged
  as ESU-only in the report
- Weights, thresholds and OS lifecycle dates are data files a customer tunes
  without touching code

**Be honest about maturity.** This is a working reference architecture, not
a shipped Red Hat product. The "top risks" ranking currently uses a simple
worst-score-first sort and is designed as a customer customisation point.
Molecule tests are on the roadmap, not implemented.

## Slides

1. Title — solution name, my name (Mark Lowcher), Red Hat
2. The gap — why Windows Server patch posture is unanswerable today
3. Solution overview — the five-stage workflow as a left-to-right diagram
4. Governance and safety — the three inventory tiers, approval gate,
   credential model. This is the "why you can trust it in prod" slide
5. The posture report — the scoring model and the six metrics; describe
   what the report looks like
6. Config as code — one playbook builds the whole AAP footprint; list the
   objects created; mention idempotency and the schedule cadence
7. Getting started — what a customer needs (AAP 2.4+, WinRM on 5986,
   service account) and the first three steps to a pilot

## Format

- Editable text and native shapes throughout, no screenshots of text
- Diagrams as real PowerPoint shapes I can edit, not images
- Speaker notes on every slide: 3–4 sentences of what I'd actually say
- Restrained, professional styling — dark text on light backgrounds, one
  accent colour, generous whitespace. No clip art or stock photos
- Max 6 bullets per slide, max ~12 words per bullet. The notes carry detail
- Do not use Red Hat's logo or trademarked brand assets
```

## Adapting it

| Situation | Change to make |
| --- | --- |
| Pure vision pitch, not a hand-off | Drop the "Be honest about maturity" paragraph |
| Internal Red Hat audience | Add the repo URL to slide 1 and ask for a demo-flow slide |
| Shorter slot | Ask for 5 slides and drop slides 4 and 6 |
| Customer has no AAP yet | Add a slide on AAP prerequisites before slide 7 |
