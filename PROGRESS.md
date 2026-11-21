# PROGRESS — Vehicle Import & Resale Intelligence Platform

Updated: 2026-11-21 | Branch: feature/stage1-foundation (PR pending) | main = S0 merged (PR #1, 36ff5fa)
Current stage: S1 done (on branch). Next: S2 after S1 merge.
Requirements: `Business_Model.txt` (watch: Honda Gold Wing GL1800/F6B, year ≥ 2018, mileage ≤ 50 000 mi).

## Stage map (full detail + DoD: `docs/plan/stages.md`)
| Stage | Content | Depends | Status |
|---|---|---|---|
| S0 | Process, PROGRESS, repo checker, CI `checks` | — | done (merged) |
| S1 | Foundation: package, config, logging, schema, self-monitoring | S0 | done (branch) |
| S2 | Import economics: watchlist match, import cost, profit/edge decision | S1 | not started |
| S3 | Collectors: auctions, local market, regulations, logistics, historical | S1 | blocked (verified sources) |
| S4 | Scheduler workflows + Streamlit dashboard | S2, S3 | not started |
| S5 | Docker Compose release + no-LLM self-monitoring acceptance | S4 | not started |

## Working logic
1. `git checkout -b feature/<topic>` from updated main. One commit per step.
2. Step test file in `tests/` named in `docs/plan/stages.md`; mark `[x] … — tests: <path>` in the same commit.
3. `python tools/check_repo.py` and `python -m pytest -q` (venv: `.venv\Scripts\python`).
4. Push → PR → CI `checks` green → `gh pr merge --squash --delete-branch` → sync main.
5. Do not start a stage whose `Depends` stages are not `done`.

## S1 — what exists
- `src/vehicle_intelligence/core/`: `config.py` (validated YAML + env `DATABASE_URL`/`LOG_LEVEL`), `logging.py` (JSON, stdout + rotating file), `database.py`.
- `src/vehicle_intelligence/models/`: auction_lot, local_listing, fee_rule, import_rule, shipment_quote, repair_estimate, collector_run.
- `scripts/init_db.py` creates schema. `monitoring/`: `tracked_run()` ledger, `evaluate()` rules (DB reachable, job never ran / stale / failure rate / stuck), CLI `python -m vehicle_intelligence.monitoring check` → exit 0 OK, 1 WARNING, 2 CRITICAL (no LLM).
- Tests: 38 pass, 1 skipped (Postgres integration).

## Open / blockers
1. Postgres 17 listens on localhost:5432 but no credentials for this project. Set `TEST_DATABASE_URL` to run the skipped schema test; do not reuse other projects' `.env`.
2. Stage S3 blocked: no verified list of auction/market/regulation sources; sites not checked yet.
3. Alembic migrations (Business_Model.txt) not added: schema is `create_all` for now; decide before S5.
4. `.env` file loading not implemented: use real environment variables.
5. Fee and regulation numbers beyond the business doc are unverified inputs.

## Next steps
1. Merge S1 PR; sync main.
2. S2.1 watchlist matching on feature branch `feature/stage2-import-economics`.

## Update rule
At the end of each session/stage: update date, stage status, done, open, next. ≤60 lines, no secrets or personal data.
