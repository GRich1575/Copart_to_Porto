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
