# Source: Copart (USA) — access rules and decision

Status: decided 2026-11-21. Owner decision: platform = Copart (USA).

## Terms found (not legal advice; verify with the owner's counsel before any automated access)
- UK Image and Data License Agreement: forbids "data scraping, page spidering, web crawling, data extraction, web scraping, page scraping ... or any other method" to obtain licensed material; limits downloads to a single sanctioned CSV. Source: https://www.copart.co.uk/Content/UK/EN/buyer/Sales/Image-and-Data-License-Agreement
- US Member Terms and Conditions: no automated-access clause located in the search results. Full US website terms not yet read: https://copart.com/Content/US/EN/Member-Terms-and-Conditions
- No official public API or data feed for anonymous lot data or sold-price history was found. Copart sits behind bot protection and requires login.
- Third-party scrapers exist (Apify actors, Bright Data). Their use is unverified against Copart's terms and is NOT used by this project.

## Decision
1. No automated scraping, crawling, or calls to Copart endpoints from this project.
2. Lot data enters through `collectors/auctions/copart_import.py`: a CSV the owner exports or copies from his own logged-in account and places in `data/raw/copart/`.
3. Before any automated access: read the full US terms, and/or ask Copart for written data-licensing terms. Only then reconsider a collector.

## Open
- Confirm the owner's Copart membership and what the account exposes (current lots, purchase history).
- Historical sold prices (S3.5) have no documented source yet.

## Search-results export (owner-saved CSV, verified 2026-11-21)
- File: "Download results" CSV from a logged-in search page. Imported by `scripts/import_copart_export.py` (adapter: `collectors/auctions/copart_search_export.py`).
- Columns used: Lot #, Make, Model, Year, VIN, Odometer, Damage description, Title code, Current bid, Sale date, Lot URL.
- Odometer "12,088 A": miles (assumed; US units), trailing " A" = actual reading. Sale date "MM/DD/YYYY hh:mm am|pm GMT"; "Future" or blank = no date.
- Observed on the 15-lot export: 2 lots above 50,900 mi (the search's odometer filter does not enforce the cap exactly); 6 lots at 0 mi without a title (may mean "not reported").

## Operating scheme (owner, 2026-11-21)
- Manual review decides eligibility for restoration; the system never auto-flags a lot.
- Purchases go through a registered Copart Broker (Member Terms: Brokers buy on Copart and sell to the customer; Copart is not a party).
- Destination: Portugal (EU). Owner is not a Russian resident or company, so the Russia/Belarus export bar does not apply to the owner's own account. Sanctions screening of the broker still applies.
- Notification to the proxy dealer contains only: lot number, auction date, lot link (`scripts/proxy_notifications.py`).
- Owner states internal use of the manual CSV is "permitted". No written confirmation from Copart is on file; the Image and Data License (Section 3) does not list internal analysis. Get written confirmation before relying on it.
