# PROGRESS — Vehicle Import & Resale Intelligence Platform

Updated: 2026-11-21 | Branch: main | Remote: github.com/GRich1575/Copart_to_Porto
Current stage: S0 (done on feature/stage0-process-setup; merge pending PR)
Requirements: `Business_Model.txt` (vehicle: Honda Gold Wing GL1800, year ≥ 2018, mileage ≤ 50 000 mi).

## Stage map (full detail + DoD: `docs/plan/stages.md`)
| Stage | Content | Depends | Status |
|---|---|---|---|
| S0 | Process, PROGRESS, repo checker, CI `checks` | — | done |
| S1 | Foundation: package, config, logging, Postgres schema, self-monitoring | S0 | not started |
| S2 | Import economics: watchlist match, import cost, profit/edge decision | S1 | not started |
| S3 | Collectors: auctions, local market, regulations, logistics, historical | S1 | not started (needs verified sources) |
| S4 | Scheduler workflows + Streamlit dashboard | S2, S3 | not started |
| S5 | Docker Compose release + no-LLM self-monitoring acceptance | S4 | not started |

## Working logic
1. `git checkout -b feature/<topic>` from updated main.
2. Implement one step; its test file in `tests/` (named in `docs/plan/stages.md`).
3. Mark step `[x] ... — tests: <path>`; run `python tools/check_repo.py` and `python -m pytest -q`.
4. Commit → `git push -u origin feature/<topic>` → `gh pr create` (body ends with attribution line).
5. CI job `checks` must be green → `gh pr merge --squash --delete-branch`.
6. Locally: `git branch -d feature/<topic>`; `git checkout main && git pull --ff-only`.
7. Do not start a stage whose `Depends` stages are not `done`.

## Done
- 2026-11-21: stage plan written (`docs/plan/stages.md`); repo checker `tools/check_repo.py` (R1–R6) with tests; CI workflow `.github/workflows/checks.yml`; `.gitignore`.

## Open / blockers
1. Python runtime for CI: 3.13 (local dev is 3.13.7; `py -3.12` not installed).
2. Stage S3 blocked: no verified list of auction/market/regulation sources; no sites checked from this environment yet.
3. Postgres 17 not installed locally; S1.4 tests need a DB URL (`TEST_DATABASE_URL`) or use SQLite fallback — decide in S1.
4. Fees/regulation numbers beyond the business doc ($350 container, ~$100 documents, 10% resale edge, 1500–2000 min edge) are unverified inputs.

## Next steps
1. Merge S0 PR; sync main.
2. S1.1 package skeleton + pyproject → S1.5 self-monitoring, one feature branch per stage.

## Update rule
At the end of each session/stage: update date, stage status, done, open, next. ≤60 lines, no secrets or personal data.
