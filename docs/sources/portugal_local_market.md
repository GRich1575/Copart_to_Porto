# Source: Portugal local used-motorcycle market (step 3.2)

Status: decided 2026-11-21. Platforms listed in config/platforms.yaml (kind: local_listing), all enabled: false.

## Platforms (from owner-supplied overview; not independently verified)
- Standvirtual (standvirtual.com/motos), OLX Portugal (olx.pt), CustoJusto (custojusto.pt),
  Facebook Marketplace, AUTO.MOTO.pt.

## Decision
1. No automated scraping of these sites until each site's terms are read and allow it (same rule as Copart).
2. Listings enter via owner-exported or owner-copied CSV: `docs/sources/local_listings_template.csv`.
3. Comparable prices are PT listings in EUR; they are not converted to USD (no FX source yet).

## Unverified claims in the overview (do not rely on them)
- "Mandatory 3-year warranty, reducible to 18 months for used vehicles": the Portuguese consumer
  sales law (DL 84/2021) sets a 3-year minimum for new goods; for used goods the minimum agreed
  period is shorter. Verify with a Portuguese lawyer or DGC before relying on any figure.
- Listing counts, platform ownership (OLX Group / Standvirtual) and feature lists: not checked.

## Comparables
- `services/comparables.py`: a listing counts only if it matches the watchlist (brand, model/variant, year ≥ min, mileage ≤ cap after km→miles). Vehicle type is assumed motorcycle (listings are from motorcycle searches only).
- Prices are EUR. Economics are USD: do not compare until an FX source is added.
