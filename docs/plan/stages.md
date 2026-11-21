# Stage plan — Vehicle Import & Resale Intelligence Platform

Source of requirements: `Business_Model.txt`.

Rules:
- Coarse unit = **stage** (`## S<n>`). Fine unit = **step** (`- [ ] n.m`).
- A step is `[x]` only when its test file (`— tests: <path>`) exists and passes.
- A stage is `Status: done` only when all its steps are `[x]` and every stage in `Depends` is `done`.
- Do not start steps of a stage whose `Depends` stages are not `done`.
- Project is "working" only when every stage is `done` and S5 acceptance passes.
- Checked by `python tools/check_repo.py` (CI job `checks`).

## S0 — Process & governance
Status: done
Depends: —
- [x] 0.1 PROGRESS.md and this stage plan — tests: tools/check_repo.py
- [x] 0.2 Repo rule checker (PROGRESS size, no tracked secrets/.env, plan consistency) — tests: tests/test_check_repo.py
- [x] 0.3 CI workflow `checks` (checker + pytest) — tests: tests/test_check_repo.py

## S1 — Foundation (config, DB, self-monitoring)
Status: done
Depends: S0
- [x] 1.1 Package skeleton, pyproject, pytest setup — tests: tests/test_skeleton.py
- [x] 1.2 Config loader (settings + countries/platforms/watchlist YAML, validated) — tests: tests/test_config.py
- [x] 1.3 Logging setup (structured, file + stdout) — tests: tests/test_logging.py
- [x] 1.4 PostgreSQL schema (SQLAlchemy 2) + init_db script — tests: tests/test_db_schema.py
- [x] 1.5 Self-monitoring: run ledger, health checks, threshold alerts, no LLM — tests: tests/test_monitoring.py

## S2 — Import economics engine (pure logic, no network)
Status: in progress
Depends: S1
- [x] 2.1 Watchlist matching (type, brand, model, year, cc, mileage cap) — tests: tests/test_watchlist.py
- [ ] 2.2 Import cost model (auction fee, transport, container, port, last mile, duties, registration) — tests: tests/test_import_cost.py
- [ ] 2.3 Profitability decision (resale ≥10% below local median, minimum edge, max bid) — tests: tests/test_profitability.py

## S3 — Data collectors (external sites; needs verified sources)
Status: not started
Depends: S1
- [ ] 3.1 Auction listings collector (USA/EU platforms) — tests: tests/test_collector_auctions.py
- [ ] 3.2 Local used-vehicle market collector — tests: tests/test_collector_local.py
- [ ] 3.3 Regulations & fees registry (country-level, cross-country rules) — tests: tests/test_collector_regs.py
- [ ] 3.4 Logistics quotes collector — tests: tests/test_collector_logistics.py
- [ ] 3.5 Historical finished-auction prices collector — tests: tests/test_collector_historical.py

## S4 — Orchestration & dashboard
Status: not started
Depends: S2, S3
- [ ] 4.1 Scheduled workflows (APScheduler jobs, independent per collector) — tests: tests/test_workflows.py
- [ ] 4.2 Streamlit dashboard (answers the 5 business questions) — tests: tests/test_dashboard.py

## S5 — Production release & acceptance
Status: not started
Depends: S4
- [ ] 5.1 Docker Compose (Postgres + app) and deployment runbook — tests: tests/test_deploy_config.py
- [ ] 5.2 End-to-end self-monitoring acceptance without LLM — tests: tests/test_acceptance.py
