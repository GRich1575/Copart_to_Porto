# PROGRESS — Vehicle Import & Resale Intelligence Platform

Updated: 2026-11-21 | Branch: feature/vin-validity (PR pending) | main = title rule merged (#8)
Current stage: S3 in progress (3.1, 3.1b done). Next: S3.2–3.5 need sources; S4 needs S3.
Requirements: `Business_Model.txt` (watch: Honda Gold Wing GL1800/F6B, year ≥ 2018, mileage ≤ 50 000 mi).
Auction platform: Copart (USA). Access: owner-exported CSV only (`docs/sources/copart.md`).

## Stage map (full detail + DoD: `docs/plan/stages.md`)
| Stage | Content | Depends | Status |
|---|---|---|---|
| S0 | Process, PROGRESS, repo checker, CI `checks` | — | done (#1) |
| S1 | Foundation: package, config, logging, schema, self-monitoring | S0 | done (#2) |
| S2 | Import economics: watchlist match, import cost, buy decision | S1 | in progress: 2.4 mileage cap on branch |
| S3 | Collectors: auctions, local market, regulations, logistics, historical | S1 | in progress: 3.1 done |
| S4 | Scheduler workflows + Streamlit dashboard | S2, S3 | not started |
| S5 | Docker Compose release + no-LLM self-monitoring acceptance | S4 | not started |

## Working logic
1. `git checkout -b feature/<topic>` from updated main. One commit per step.
2. Step test file in `tests/` named in `docs/plan/stages.md`; mark `[x] … — tests: <path>` in the same commit.
3. `python tools/check_repo.py` and `python -m pytest -q` (venv: `.venv\Scripts\python`).
4. Push → PR → CI `checks` green → `gh pr merge --squash --delete-branch` → sync main.
5. Do not start a stage whose `Depends` stages are not `done`.

## S3 — what exists
- `collectors/auctions/copart_search_export.py` + `scripts/import_copart_export.py`: owner's search-results CSV → auction_lot. Run on 2026-11-21 export: 15 accepted, 0 rejected (local SQLite `data/local.db`, not versioned).
- `collectors/auctions/copart_import.py`: CSV import (template `docs/sources/copart_import_template.csv`), per-row validation, upsert by (copart_us, lot_id), rejected rows logged with line numbers, run in `collector_run` (job `copart_import`).
- Mileage rule (owner, 2026-11-21): hard cap = 50 000 + 10 000 tolerance = 60 000 mi (step 2.4).
- Tests: 86 pass, 1 skipped (Postgres integration).
- Title rule (owner, 2026-11-21, step 3.1c): lots without title are rejected at import and deleted from the local DB (`--discard-excluded`). Local DB now: 4 lots (all titled, ≤ 60 000 mi).
- VIN rule (owner, 2026-11-21, step 3.1d): masked or partially masked VIN (contains '*') = kept; blank = kept; fully visible but malformed (not 17 chars, I/O/Q, or wrong North-American check digit) = excluded and discarded. Local DB: all 4 stored lots masked, so none discarded.

## Open / blockers
0. Copart automated access: owner has chosen the CSV route; the live-scrape request was declined pending the terms. US terms fetch returned no text.
1. Copart: UK licence bans scraping; US terms not yet read; no official API found. No automated Copart access is built. Owner to decide: read full US terms and/or request written data-licence terms from Copart before any automated collector.
2. Historical sold prices (3.5): no documented source yet (Copart purchase history in the owner's account is the candidate).
3. 3.2 local market, 3.3 regulations, 3.4 logistics: need sources (destination country not chosen yet).
4. Postgres: no project credentials; set `TEST_DATABASE_URL` to run the skipped test.
5. Alembic not added; decide before S5. `.env` loading not implemented.
6. Economics: min_edge 1500 (lower bound) vs 2000; fee rates unset.

## Next steps
1. Merge VIN-validity PR; sync main. 2. S3.2 sources (owner).
2. Owner: destination EU country, local-market sources (3.2), Copart CSV export path.

## Update rule
At the end of each session/stage: update date, stage status, done, open, next. ≤60 lines, no secrets or personal data.
