#!/usr/bin/env python3
"""
Posture grade filters for the Windows patching report.

Exposes four Jinja2 filters loaded by Ansible at runtime:
  - posture_grade_host(host_facts, weights, thresholds, lifecycle)
  - posture_grade_fleet(host_postures, weights, thresholds)
  - top_risks_ranking(host_postures, top_n)        <-- user-contributed logic
  - days_since_iso(iso_timestamp)
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Any


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------

def _parse_iso(ts: str) -> datetime | None:
    if not ts:
        return None
    try:
        # Accept trailing Z by replacing with +00:00 for fromisoformat.
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _merge_phases(records: list[dict]) -> dict:
    """Combine scan + install records for one host into a single view."""
    scan = next((r for r in records if r.get("phase") == "scan"), {})
    install = next((r for r in records if r.get("phase") == "install"), {})
    return {
        "hostname": (scan.get("hostname") or install.get("hostname")),
        "os": scan.get("os") or install.get("os") or {},
        "scan_time": scan.get("scan_time"),
        "install_time": install.get("install_time"),
        "missing_updates": install.get("still_missing_after_install")
                            or scan.get("missing_updates") or [],
        "installed": install.get("installed") or [],
        "failed_updates": install.get("failed") or [],
        "rebooted": install.get("rebooted", False),
        "pending_reboot_before_scan": scan.get("pending_reboot_before_scan", False),
        "last_successful_patch": install.get("install_time")
                                  or scan.get("last_successful_patch"),
        "error": install.get("error"),
    }


def _classify_lifecycle(os_data: dict, lifecycle: dict, near_eos_days: int) -> str:
    """Returns one of: supported | near_eos | past_eos | unknown."""
    if not os_data or not lifecycle:
        return "unknown"
    # Naive key match — README documents how to extend lifecycle table.
    version = (os_data.get("version") or "").lower()
    product = (os_data.get("product") or "").lower()
    matched_key = None
    for key in lifecycle.keys():
        norm = key.replace("_", " ").lower()
        if norm in product or norm in version or key.split("_")[-1] in version:
            matched_key = key
            break
    if not matched_key:
        return "unknown"
    ext_end = _parse_iso(lifecycle[matched_key].get("extended_end") or "")
    if not ext_end:
        return "unknown"
    today = _now()
    delta_days = (ext_end - today).days
    if delta_days <= 0:
        return "past_eos"
    if delta_days <= near_eos_days:
        return "near_eos"
    return "supported"


def _hours_since(ts: str) -> float | None:
    dt = _parse_iso(ts)
    if not dt:
        return None
    return (_now() - dt).total_seconds() / 3600.0


# ----------------------------------------------------------------------------
# Per-host grading
# ----------------------------------------------------------------------------

def posture_grade_host(records: list[dict], weights: dict, thresholds: dict,
                       lifecycle: dict) -> dict:
    h = _merge_phases(records)

    missing = h["missing_updates"] or []
    missing_count = len(missing)
    critical_or_sec = [u for u in missing
                       if any(c in (u.get("categories") or [])
                              for c in ("SecurityUpdates", "CriticalUpdates"))]

    # --- security_currency (30) ---
    if missing_count == 0:
        security_currency = 100.0
    elif len(critical_or_sec) == 0:
        security_currency = 80.0
    else:
        # Linear penalty: 5pts per missing critical/security KB, floor 0.
        security_currency = max(0.0, 100.0 - 20.0 * len(critical_or_sec))

    # --- ism_sla (20) ---
    install_hours = _hours_since(h.get("install_time") or "")
    if install_hours is None:
        ism_sla = 50.0   # neutral when unknown
    elif install_hours <= thresholds["ism_critical_hours"]:
        ism_sla = 100.0
    elif install_hours <= thresholds["ism_standard_days"] * 24:
        ism_sla = 75.0
    else:
        ism_sla = max(0.0, 75.0 - (install_hours / 24 - thresholds["ism_standard_days"]) * 5)

    # --- reboot_hygiene (15) ---
    reboot_hygiene = 0.0 if h.get("pending_reboot_before_scan") else 100.0

    # --- lifecycle (15) ---
    lc_status = _classify_lifecycle(
        h.get("os") or {}, lifecycle or {},
        thresholds.get("lifecycle_near_eos_days", 365)
    )
    lifecycle_score = {"supported": 100.0, "near_eos": 60.0,
                       "past_eos": 0.0, "unknown": 50.0}[lc_status]

    # --- patch_recency (10) ---
    last_patch_hours = _hours_since(h.get("last_successful_patch") or "")
    if last_patch_hours is None:
        patch_recency = 50.0
    else:
        days = last_patch_hours / 24
        target = thresholds.get("recency_days_target", 35)
        patch_recency = 100.0 if days <= target else max(0.0, 100.0 - (days - target) * 2)

    # --- failure_rate (10) ---
    failure_rate = 0.0 if (h.get("failed_updates") or h.get("error")) else 100.0

    # Weighted total
    components = {
        "security_currency": security_currency,
        "ism_sla": ism_sla,
        "reboot_hygiene": reboot_hygiene,
        "lifecycle": lifecycle_score,
        "patch_recency": patch_recency,
        "failure_rate": failure_rate,
    }
    score = sum(components[k] * weights[k] / 100.0 for k in components)
    score = round(score, 1)
    grade = ("A" if score >= 90 else "B" if score >= 80 else
             "C" if score >= 70 else "D" if score >= 60 else "F")

    return {
        "grade": grade,
        "score": score,
        "components": components,
        "missing_count": missing_count,
        "critical_or_security_missing": len(critical_or_sec),
        "pending_reboot": h.get("pending_reboot_before_scan", False),
        "lifecycle_status": lc_status,
        "last_patch_age_days": (last_patch_hours / 24) if last_patch_hours else None,
        "failed_count": len(h.get("failed_updates") or []),
        "merged": h,
    }


# ----------------------------------------------------------------------------
# Fleet grading
# ----------------------------------------------------------------------------

def posture_grade_fleet(host_postures: list[dict], weights: dict,
                        thresholds: dict) -> dict:
    if not host_postures:
        return {"grade": "F", "score": 0, "host_count": 0,
                "compliant": 0, "at_risk": 0}
    scores = [hp["posture"]["score"] for hp in host_postures]
    avg = round(sum(scores) / len(scores), 1)
    grade = ("A" if avg >= 90 else "B" if avg >= 80 else
             "C" if avg >= 70 else "D" if avg >= 60 else "F")
    compliant = sum(1 for hp in host_postures
                    if hp["posture"]["grade"] in ("A", "B"))
    at_risk = sum(1 for hp in host_postures
                  if hp["posture"]["grade"] in ("D", "F"))
    return {
        "grade": grade,
        "score": avg,
        "host_count": len(host_postures),
        "compliant": compliant,
        "at_risk": at_risk,
        "compliant_pct": round(compliant * 100.0 / len(host_postures), 1),
    }


# ----------------------------------------------------------------------------
# Top risks ranking
#
# === USER CONTRIBUTION POINT ===
# This function decides which hosts surface in the "Top Risks" section of the
# report. There are multiple valid ranking strategies — pick the one that
# matches how your Windows administrators triage:
#
#   (a) Lifecycle-first  : EoS hosts always top, then grade ascending
#   (b) Severity-weighted: count(critical_KBs) * age_days, descending
#   (c) Composite        : invert(score) + lifecycle_bonus + reboot_age_bonus
#   (d) Pure grade       : sort by score ascending, take top_n
#
# Default (placeholder) implementation = (d) pure grade. Replace with the
# 5-10 lines that reflect your team's prioritisation approach.
# ----------------------------------------------------------------------------

def top_risks_ranking(host_postures: list[dict], top_n: int = 5) -> list[dict]:
    """Return the top_n hosts ranked by risk (highest risk first)."""

    # TODO: Replace this placeholder with your preferred ranking logic.
    # The placeholder ranks by ascending score (worst grade first).
    ranked = sorted(host_postures, key=lambda hp: hp["posture"]["score"])

    out = []
    for hp in ranked[:top_n]:
        p = hp["posture"]
        reason_parts = []
        if p["lifecycle_status"] == "past_eos":
            reason_parts.append("OS past extended support")
        elif p["lifecycle_status"] == "near_eos":
            reason_parts.append("OS near end-of-support")
        if p["critical_or_security_missing"]:
            reason_parts.append(
                f"{p['critical_or_security_missing']} critical/security KBs missing"
            )
        if p["pending_reboot"]:
            reason_parts.append("pending reboot")
        if p["failed_count"]:
            reason_parts.append(f"{p['failed_count']} failed updates")
        out.append({
            "hostname": hp["hostname"],
            "grade": p["grade"],
            "score": p["score"],
            "reason": "; ".join(reason_parts) or "Low posture score",
        })
    return out


# ----------------------------------------------------------------------------
# Misc
# ----------------------------------------------------------------------------

def days_since_iso(ts: str) -> int:
    dt = _parse_iso(ts)
    if not dt:
        return -1
    return (_now() - dt).days


# ----------------------------------------------------------------------------
# Ansible filter plugin registration
# ----------------------------------------------------------------------------

class FilterModule(object):
    def filters(self):
        return {
            "posture_grade_host":   posture_grade_host,
            "posture_grade_fleet":  posture_grade_fleet,
            "top_risks_ranking":    top_risks_ranking,
            "days_since_iso":       days_since_iso,
        }
