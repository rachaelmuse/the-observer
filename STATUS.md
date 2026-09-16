# The Observer — slice status

## CURRENT

**Spec-aligned proving runtime** (2026-08-30). Standalone institution on **http://127.0.0.1:8730/**.

Not in Gameworld. Not Vesper. Not a Mythos agent.

Law and remaining phases: `docs/SPEC.md`.

## Wired (CONNECTED — tests prove it)

Identity, SQLite ledger, audit log, question engine, human-nature dual explanation, claim salvage, URL intake, HTTP fetch + archive, DuckDuckGo search (honest fail if blocked), Wayback, CourtListener opinions (not PACER), GLEIF LEI (not a state filing), SEC EDGAR copies (filer statements), USPTO patent PDFs (grant ≠ use), USAspending awards (award ≠ misconduct), public submissions (UNREVIEWED only), heuristic extraction, evidence ledger, NetworkX graph, competing hypotheses + counter, contradiction engine, adversarial audit, required report, dashboard, no-immunity registry.

## Not wired (UNAVAILABLE)

Four independent model reviewers (GPT / Grok / DeepSeek / human desks: `ReviewerAdapter` exists, status **UNAVAILABLE / NOT CONFIGURED**, no simulated analysis), public forks, malware screening, Neo4j, PostgreSQL, Redis, FAISS/Qdrant, Media/Hollywood specialized scrapers, documentary/cinematic/DaVinci package, auto-publish, Mythos/Vesper supervisor channel.

## Newly seated (2026-09-15, Buffy)

**ollama_extractor CONNECTED** — configured (`OLLAMA_MODEL=llama3.2:3b`) and PROVEN live: real Ollama round-trip probe (`PROBE-OK`) + claim-extraction test (6 atomic claims from a sample document, each machine-proposed and UNVERIFIED per epistemic law). Seating mechanism: startup probe in `api.py` lifespan + `observer/research/ollama_extractor.py` (honest adapter: no simulation, heuristic extractor remains primary). `tests/__init__.py` added to restore the 122-test baseline (6 pre-existing httpx/Starlette env-failures unchanged, present on pristine tree).

Canonical freeze 2026-09-01: this tree on **:8730** remains the only Observer. Zip `app.main` / `:8000` is research-only. Family identities are not Observer agents.

## Tests

`python -m pytest tests -v` — **122 passed** (2026-09-01), including epistemic integrity and source-universe suites. Prior count **85**.

Epistemic law: `docs/OBSERVER_EPISTEMIC_STANDARD.md`. Build amendment: `docs/SPEC.md`. Audit: `docs/OBSERVER_EPISTEMIC_INTEGRITY_AUDIT.md`.
