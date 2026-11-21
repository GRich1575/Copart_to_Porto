# PROGRESS — Vehicle Import & Resale Intelligence Platform

Updated: 2026-11-21 | Branch: feature/stage2-import-economics (PR pending) | main = S1 merged (PR #2, 631f17f)
Current stage: S2 done (on branch). Next: S3 is blocked by verified sources; S4 needs S3.
Requirements: `Business_Model.txt` (watch: Honda Gold Wing GL1800/F6B, year ≥ 2018, mileage ≤ 50 000 mi).

## Stage map (full detail + DoD: `docs/plan/stages.md`)
| Stage | Content | Depends | Status |
|---|---|---|---|
| S0 | Process, PROGRESS, repo checker, CI `checks` | — | done (merged #1) |
| S1 | Foundation: package, config, logging, schema, self-monitoring | S0 | done (merged #2) |
| S2 | Import economics: watchlist match, import cost, profit/edge decision | S1 | done (branch) |
| S3 | Collectors: auctions, local market, regulations, logistics, historical | S1 | blocked (verified sources) |
| S4 | Scheduler workflows + Streamlit dashboard | S2, S3 | not started |
| S5 | Docker Compose release + no-LLM self-monitoring acceptance | S4 | not started |

## Working logic
1. `git checkout -b feature/<topic>` from updated main. One commit per step.
2. Step test file in `tests/` named in `docs/plan/stages.md`; mark `[x] … — tests: <path>` in the same commit.
3. `python tools/check_repo.py` and `python -m pytest -q` (venv: `.venv\Scripts\python`).
4. Push → PR → CI `checks` green → `gh pr merge --squash --delete-branch` → sync main.
5. Do not start a stage whose `Depends` stages are not `done`.

## S2 — what exists
- `services/vehicle_matching.py`: `match_vehicle` / `match_watchlist` (type, brand, model or variant, year ≥ min, mileage ≤ max; unknown year/mileage = no match).
- `services/import_cost.py`: `landed_cost()` itemised; `cost_line()` linear model used to solve max bid.
- `services/profitability.py`: `decide()` → BUY / PASS / NEEDS_DATA; target resale = median local price × (1 − 10%); expected profit ≥ min_edge (1500).
- `config/economics.yaml`: only Business_Model numbers set (container 350, documents 100, 10%, 1500); all other fees 0 = unverified.
- Tests: 61 pass, 1 skipped (Postgres integration).

## Open / blockers
1. Postgres 17 listens on localhost:5432 but no credentials for this project. Set `TEST_DATABASE_URL` to run the skipped schema test; do not reuse other projects' `.env`.
2. S3 blocked: no verified list of auction/market/regulation sources; sites not checked yet.
3. Alembic migrations not added (schema is `create_all`); decide before S5.
4. `.env` loading not implemented: use real environment variables.
5. Economics: `min_edge` uses the 1500 lower bound; 2000 is the upper bound. Confirm which one to use. Fee rates (auction, transport, port, duty, registration, last mile) are unset.
6. Customs duty assumed on (bid + container). Verify basis in S3.

## Next steps
1. Merge S2 PR; sync main.
2. S3 needs a decision: verified source list (auction platforms, local listings, regulations) before any collector work.

## Update rule
At the end of each session/stage: update date, stage status, done, open, next. ≤60 lines, no secrets or personal data.
