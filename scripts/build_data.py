#!/usr/bin/env python3
"""
Build data/dashboard_data.json from data/technologies_db.py,
data/deals_db.py, and data/internal_targets.json.

This is the ONLY script a routine data refresh needs to run:

    python scripts/build_data.py

No dependencies beyond the Python standard library -- nothing to pip
install.

Routine update workflow (this is the whole thing):
  1. Add or edit an entry in data/technologies_db.py (new/updated
     technology) and/or data/deals_db.py (new deal or news finding). Both
     are plain Python -- edit them directly, no spreadsheet tool needed.
  2. Edit data/internal_targets.json directly if an internal target or the
     reference product's numbers change (it's hand-maintained, not
     generated -- there's no spreadsheet it comes from).
  3. Run this script.
  4. Commit the regenerated data/dashboard_data.json along with whichever
     db file(s) changed.

Nothing in index.html, assets/app.js, or assets/styles.css should ever need
to change for a normal data update -- they only ever read
dashboard_data.json.
"""
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
INTERNAL_JSON = DATA_DIR / "internal_targets.json"
OUTPUT_JSON = DATA_DIR / "dashboard_data.json"

sys.path.insert(0, str(DATA_DIR))
from technologies_db import TECHNOLOGIES  # noqa: E402
from deals_db import DEALS  # noqa: E402

# Ordered earliest -> most mature. Order matters: it drives the x-axis order
# in the scatter chart and the ordinal color ramp for stage badges.
STAGE_BUCKETS = [
    "Research / Academic",
    "Preclinical",
    "Platform / Feasibility",
    "Pre-registration / Late-stage",
    "Approved / Marketed",
]
STAGE_OTHER = "Varies by Program"

# Substring rules, checked in order, against the raw stage text (lowercased).
# First match wins. "stage_raw" in technologies_db.py is meant to be messy
# free text (e.g. "Commercial (lead product approved); platform extension in
# Phase III") -- these rules pick the most senior/leading status mentioned.
# If a new entry's stage text doesn't match any rule here, it silently falls
# into "Varies by Program" -- check the WARNING this script prints and add a
# rule if that's wrong.
STAGE_RULES = [
    ("varies by partner program", STAGE_OTHER),
    ("approved", "Approved / Marketed"),
    ("commercially available", "Approved / Marketed"),
    ("commercial (", "Approved / Marketed"),
    ("pre-registration", "Pre-registration / Late-stage"),
    ("platform", "Platform / Feasibility"),
    ("research", "Research / Academic"),
    ("academic", "Research / Academic"),
    ("preclinical", "Preclinical"),
]

CONCENTRATION_BUCKETS = [
    (0, 300, "< 300 mg/mL"),
    (300, 450, "300–450 mg/mL"),
    (450, 600, "450–600 mg/mL"),
    (600, float("inf"), "600+ mg/mL"),
]
CONCENTRATION_NOT_DISCLOSED = "Not disclosed"

DATE_RE = re.compile(r"\d{4}(-\d{2}(-\d{2})?)?")


def classify_stage(raw):
    if not raw:
        return STAGE_OTHER
    low = raw.lower()
    for needle, bucket in STAGE_RULES:
        if needle in low:
            return bucket
    print(f"WARNING: stage text did not match any rule, filed under "
          f"'{STAGE_OTHER}': {raw!r}", file=sys.stderr)
    return STAGE_OTHER


def classify_concentration(value):
    if not isinstance(value, (int, float)):
        return CONCENTRATION_NOT_DISCLOSED
    for lo, hi, label in CONCENTRATION_BUCKETS:
        if lo <= value < hi:
            return label
    return CONCENTRATION_NOT_DISCLOSED


def date_sort_key(value):
    """Best-effort recency key for a deal's date. Handles a clean ISO string
    ("2026-08-05"), a bare year ("2026"), or free text with an embedded date
    ("2022-11 (option); converted to exclusive worldwide license"). Picks
    the *latest* year/month/day mentioned anywhere in the text. Returns -1
    if nothing parses, so fully undated entries sort last."""
    if not value:
        return -1
    text = str(value)
    best = -1
    for m in DATE_RE.finditer(text):
        parts = m.group(0).split("-")
        y = int(parts[0])
        mo = int(parts[1]) if len(parts) > 1 else 1
        d = int(parts[2]) if len(parts) > 2 else 1
        key = y * 10000 + mo * 100 + d
        if key > best:
            best = key
    return best


def build_deal(d):
    return {
        "deal_id": d.get("deal_id"),
        "partner": d.get("partner") or "N/A",
        "deal_type": d.get("deal_type") or "N/A",
        "date": d.get("date") or "Undated",
        "date_sort_key": date_sort_key(d.get("date")),
        "summary": d.get("summary") or "",
        "molecule": d.get("molecule"),
        "source_name": d.get("source_name") or "",
        "source_url": d.get("source_url"),
        "relevance": d.get("relevance"),
        "confidence": d.get("confidence"),
        "flagged": bool(d.get("flagged")),
        "new_in_digest": bool(d.get("new_in_digest")),
    }


def main():
    if not INTERNAL_JSON.exists():
        print(f"Missing required input: {INTERNAL_JSON}", file=sys.stderr)
        sys.exit(1)

    internal_cfg = json.loads(INTERNAL_JSON.read_text(encoding="utf-8"))

    deals_by_tid = {}
    for d in DEALS:
        tid = d.get("technology_id")
        if not tid:
            continue
        deals_by_tid.setdefault(tid, []).append(d)

    # Deals whose technology_id matches one of these aliases belong to an
    # internal target, not an external technology (see internal_targets.json).
    alias_to_internal = {}
    for t in internal_cfg.get("internal_targets", []):
        for alias in t.get("deal_id_aliases", []):
            alias_to_internal[alias] = t["id"]

    # ---------------- technologies ----------------
    technologies = []
    used_tids = set()
    for d in TECHNOLOGIES:
        tid = d.get("id")
        used_tids.add(tid)
        raw_stage = (d.get("stage_raw") or "").strip()
        raw_conc = d.get("concentration_numeric")
        conc_numeric = raw_conc if isinstance(raw_conc, (int, float)) else None

        own_deals = [build_deal(x) for x in deals_by_tid.get(tid, [])]
        own_deals.sort(key=lambda x: x["date_sort_key"], reverse=True)

        technologies.append({
            "id": tid,
            "name": d.get("name"),
            "company": d.get("company"),
            "stage_raw": raw_stage,
            "stage_bucket": classify_stage(raw_stage),
            "type": d.get("type"),
            "concentration_text": d.get("concentration_text"),
            "concentration_numeric": conc_numeric,
            "concentration_bucket": classify_concentration(conc_numeric),
            "needle_size": d.get("needle_size"),
            "mechanism": d.get("mechanism"),
            "date_added": d.get("date_added"),
            "last_reviewed": d.get("last_reviewed"),
            "deals": own_deals,
            "is_internal": False,
            "is_reference": False,
        })

    # Newest-reviewed first, so the dashboard table and the daily digest
    # agree on what's "new" without either one re-deriving order on its own.
    # Entries with no last_reviewed (shouldn't normally happen) sort last.
    technologies.sort(key=lambda r: r["last_reviewed"] or "", reverse=True)

    # ---------------- internal targets / reference products ----------------
    internal_targets = []
    for t in internal_cfg.get("internal_targets", []):
        aliases = t.get("deal_id_aliases", [])
        notes = [build_deal(x) for tid in aliases for x in deals_by_tid.get(tid, [])]
        record = {k: v for k, v in t.items() if k != "deal_id_aliases"}
        record["notes"] = notes
        record["is_internal"] = True
        record["is_reference"] = False
        internal_targets.append(record)

    reference_products = []
    for t in internal_cfg.get("reference_products", []):
        record = dict(t)
        record["is_internal"] = False
        record["is_reference"] = True
        reference_products.append(record)

    # ---------------- data hygiene: catch deal entries that reference nothing ----------------
    known_tids = used_tids | set(alias_to_internal.keys())
    unmatched = sorted(set(deals_by_tid.keys()) - known_tids)
    if unmatched:
        print(f"WARNING: {len(unmatched)} deal entr(y/ies) reference unknown "
              f"technology_id(s), excluded from output: {unmatched}", file=sys.stderr)

    # ---------------- orderings (fixed here, dashboard must not re-sort) ----------------
    stage_order = STAGE_BUCKETS + [STAGE_OTHER]
    type_counts = {}
    for r in technologies:
        if r["type"]:
            type_counts[r["type"]] = type_counts.get(r["type"], 0) + 1
    type_order = sorted(type_counts, key=lambda t: (-type_counts[t], t))
    company_order = sorted({r["company"] for r in technologies if r["company"]})
    concentration_order = [b[2] for b in CONCENTRATION_BUCKETS] + [CONCENTRATION_NOT_DISCLOSED]

    # ---------------- counts ----------------
    deals_tracked = sum(len(v) for tid, v in deals_by_tid.items() if tid in used_tids)
    flagged_deals = sum(
        1 for tid, v in deals_by_tid.items() if tid in used_tids
        for x in v if x.get("flagged")
    )
    commercial = sum(1 for r in technologies if r["stage_bucket"] == "Approved / Marketed")
    comparable = sum(1 for r in technologies if r["concentration_numeric"] is not None)
    comparable += sum(1 for r in internal_targets if r.get("concentration_numeric") is not None)

    last_reviewed_dates = [r["last_reviewed"] for r in technologies if r["last_reviewed"]]

    # ---------------- recent activity feed ----------------
    recent_activity = []
    for r in technologies:
        for dl in r["deals"]:
            recent_activity.append({**dl, "technology_id": r["id"], "technology_name": r["name"]})
    recent_activity.sort(key=lambda x: x["date_sort_key"], reverse=True)
    recent_activity = recent_activity[:15]

    payload = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "generated_from": {"technologies": "technologies_db.py", "deals": "deals_db.py"},
        "last_updated": max(last_reviewed_dates) if last_reviewed_dates else None,
        "stage_order": stage_order,
        "type_order": type_order,
        "company_order": company_order,
        "concentration_order": concentration_order,
        "counts": {
            "tracked": len(technologies) + len(internal_targets),
            "comparable": comparable,
            "commercial": commercial,
            "deals_tracked": deals_tracked,
            "flagged_deals": flagged_deals,
        },
        "internal_targets": internal_targets,
        "reference_products": reference_products,
        "technologies": technologies,
        "recent_activity": recent_activity,
    }

    OUTPUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(technologies)} technologies, {len(internal_targets)} internal targets, "
          f"{deals_tracked} deals ({flagged_deals} flagged) -> {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
