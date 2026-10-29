# Current operations

The application covers Thailand. [Current scope](current-scope.md) is authoritative; retired local experiments are under `archive/` and do not define preferences or defaults.

## Collection and publication

- GISTDA: `python -m pipelines.gistda.run --publish` collects the complete bounded **3days Thailand** query and publishes its chunked A/B generation. `--three-day` is an equivalent explicit option. There is no district publisher or default district filter.
- Daily weather: `python -m pipelines.open_meteo.run --level all --publish`.
- Hourly weather: `python -m pipelines.open_meteo.hourly --publish`.
- RID: `python -m pipelines.rid.run --publish`.
- TMD: `python -m pipelines.tmd.run --publish`.

Use existing server-side repository secrets. Never put provider keys or MongoDB credentials into browser inputs, URLs, reports or committed files. The Python runners do not automatically load .env files.

## GitHub Actions

Seven active workflows cover checks, daily/hourly weather, RID, TMD, national GISTDA publication and national GISTDA inspection. The inspector form contains only service and window; 3days is the default and all queries are unfiltered. Other explicitly selected windows remain diagnostics only and never become a publication fallback.

`gistda.yml` targets 09:27 ICT daily. `gistda-access.yml` has no schedule and reads one diagnostic page without database writes. The former local candidate workflow is retired. Empty results do not establish safe conditions or full satellite coverage.

## Read APIs and health

[Data health](https://hazard-intelligence-lime.vercel.app/health) separates failed collection, overdue schedule, data freshness and source-quality issues. Reloading the page does not trigger provider collection. GitHub scheduling and API/CDN caches can delay visible updates.

Use `/api/flood-products?view=summary` for the national count without geometry. Add a canonical area_id to select any region, province or district. `view=detail` loads only that area's pages and pins one generation until its complete count is verified. The initial national view does not fetch all geometry; explicitly enabling the national layer does.

## Verify and recover

`python -m scripts.mongo_admin verify` checks only the five active product families. Historical stored products are audited only with `--include-retired`; normal Actions do not report them as active integrations. Retention remains bounded and failed refreshes keep the previous complete generation.

`python -m scripts.mongo_admin rollback --source gistda` restores a validated previous three-day slot. Never delete stored snapshots or run history merely to change defaults.

Run `python -m pytest -q`, `npm run typecheck`, `npm run test:web` and `npm run build` for code changes. Synthetic local snapshots must remain ignored and are disabled in production.

HII targets the unfiltered national station response and remains unavailable until observation semantics are accepted. See [the current HII review](thaiwater-access-review-2026-10-29.md).
