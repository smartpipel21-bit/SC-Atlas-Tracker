# SC Atlas Tracker — High-Concentration SC Injection Pipeline

A static, no-build dashboard tracking high-concentration subcutaneous (SC) injection
technologies: who owns them, what stage they're at, what concentration they've
demonstrated, and how they work.

Modeled on a competitive-intelligence dashboard layout (sidebar nav, stat tiles,
filterable table, "recently reviewed" feed, part-to-whole donut) and built against
the real technology database provided (`data/Technologies_source.xlsx`, 22 entries
across 22 companies).

## Status

This is dashboard **code only** — it has not been deployed. Open `index.html`
through any static file server (see below) to view it locally. Deployment
(GitHub Pages, Vercel, S3, wherever) is up to you.

## Structure

```
index.html              the dashboard page (no build step, no framework)
assets/styles.css        all styling
assets/app.js             fetches data/technologies.json and renders everything
data/Technologies_source.xlsx   the source spreadsheet you provided
data/technologies.json    generated data file the dashboard actually reads
scripts/build_data.py     regenerates technologies.json from the source xlsx
```

## Viewing it locally

Any static file server works, e.g.:

```
cd SC-Atlas-Tracker
python3 -m http.server 8000
# open http://localhost:8000
```

Opening `index.html` directly via `file://` will *not* work — the browser blocks
the `fetch()` call that loads `data/technologies.json` from a local file path.
A local server (or any real static host) is required.

## Updating the data

1. Replace `data/Technologies_source.xlsx` with the updated spreadsheet (keep the
   same column headers — see `scripts/build_data.py` for the exact names expected).
2. Run:
   ```
   python3 scripts/build_data.py
   ```
3. Commit the regenerated `data/technologies.json` along with the new source file.

The script also normalizes two fields the dashboard depends on:

- **`stage_bucket`** — the raw "Development Stage" text is messy free text (varies
  wildly row to row); the script buckets it into six categories (Research /
  Academic → Preclinical → Platform / Feasibility → Pre-registration / Late-stage →
  Approved / Marketed, plus a "Varies by Program" catch-all) that drive both the
  filter dropdown and the stage badge color. If you add a row whose stage text
  doesn't match any existing rule, check `STAGE_RULES` in `scripts/build_data.py`
  and add a rule for it — otherwise it silently falls into "Varies by Program."
- **`concentration_bucket`** — the numeric mg/mL column bucketed into ranges for
  the concentration filter. Rows without a numeric value show as "Not disclosed."

## Design notes / deliberate omissions vs. the reference mockup

- **No fabricated "verified sources" count or "Source verified" badge.** The
  source spreadsheet has no citation/verification metadata, so a stat or badge
  claiming that would be inventing data. If you want that feature, it needs a
  real sources column added to the spreadsheet first.
- **Sidebar nav** only has a working "Dashboard" page. "Companies" and
  "Methodology" are shown (matching the reference layout) but are visually
  disabled — there's no data or content behind them yet.
- **Colors** follow a validated, colorblind-checked palette (categorical hues for
  technology type, an ordinal light→dark ramp for stage maturity) rather than
  arbitrary picks — see the color comments at the top of `assets/styles.css`.
  Every color-coded value also has a text label next to it, so nothing depends on
  color alone.
- **Dark mode** was not built — the reference mockup is light-only and this
  matches it. Flagging it as a known gap rather than silently skipping it.
- **CSV export** exports whatever the current filters show, not just the full set.

## Data caveats worth knowing before you present this

- Several rows' "Development Stage" text describes a mix of statuses in one cell
  (e.g. "Commercial (lead product approved); platform extension in Phase III").
  The bucketing picks the most senior/leading status — check `stage_raw` in
  `data/technologies.json` (or the detail row on each dashboard entry) before
  citing a specific stage in a deck.
- 10 of 22 technologies have no disclosed numeric concentration. They show as
  "Not disclosed," not zero — don't let the donut/table give the impression the
  dataset is more complete than it is.
