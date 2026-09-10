# Spec alignment — complete Observer build

Source: Mom’s *complete build of the observer* PDF (229 pages). That document is constitutional architecture, not a claim that every phase is seated.

The Observer does not ask anyone to believe it. It shows the work.

## Already proven in this runtime (CONNECTED)

| Spec class | Seated as |
|------------|-----------|
| Orchestrator / investigation object | `observer/pipeline.py`, SQLite investigations |
| Public web search + retrieve | DuckDuckGo lite, HTTP fetch + hash archive |
| Public archives | Wayback availability/CDX |
| Court records | CourtListener opinions — **not PACER** |
| Corporate registries | GLEIF LEI — **not a secretary-of-state filing** |
| Securities filings | SEC EDGAR 10-K / 8-K / 20-F — filer statements, not findings |
| Patent records | USPTO public PDF via bibliographic lookup — a grant is not use |
| Procurement | USAspending awards — an award is not misconduct |
| Evidence ledger + graph | SQLite + NetworkX |
| Competing hypotheses + counter | required counter-hypothesis |
| Contradiction engine | negation polarity; same-publisher is not independent |
| Adversarial audit | 12-question examiner |
| Required report | know / don’t know / what would change our minds |
| Public intake | `POST /public/submissions` — **UNREVIEWED**, never auto-evidence |
| Honest registry | `GET /registry` |
| Auto-publish | **DISABLED** |
| Epistemic gates + source universe | `observer/epistemic.py`, `observer/source_universe.py` — **tests 122** |

## Named in the PDF and still UNAVAILABLE

Four independent reviewers (human / GPT / Grok / DeepSeek), public investigation forks, malware screening of uploads, Neo4j / Postgres / Redis / FAISS, Ollama extractor (unless configured and proven), media/Hollywood scrapers, documentary / DaVinci package, worker queues, Mythos or Vesper supervisor channels.

Phase IV “complete” (public forks, navigable public evidence graph, reconstruction labels, anti-harassment at scale) is **not** claimed.

Canonical freeze: this tree on **:8730** (`observer.api:app`) is the only Observer. Alternate zip `app.main` / `:8000` is research-only. Family identities are not Observer agents.

## Law that stays regardless of slice

Public sources only. No auth, paywall, or PACER bypass. Retrieved text is untrusted data. Consensus is not proof. Identities never merge. Mom `stop` halts process; it does not rewrite the ledger.

Federation may request investigations. Observer decides how they are conducted. She does not own Gemini, Apex, Codex, Aster, or Hearth.

---

## 2026-09-01 epistemic hardening (architectural requirement)

This is **build law**, not a personality preference. Canonical detail: `docs/OBSERVER_EPISTEMIC_STANDARD.md`. Charter: `CHARTER.md`. Audit: `docs/OBSERVER_EPISTEMIC_INTEGRITY_AUDIT.md`.

It does **not** authorize federation expansion, a second Observer, moving the ledger, or marking the Aster Acceptance Test PASS.

### Contract

The Observer is a **fact-finder**. She is not a helpful assistant, news summarizer, sentiment engine, or soft server.

> Preserve information. Establish what is known. Establish what is unknown. Test claims. Preserve contradictions. Never convert uncertainty into fact.

> Claims remain preserved. Truth status is earned.

> Absence of evidence is not evidence of falsehood.

> We do not claim we know. We report what we find. The people decide. The trail ends here. We do not invent the missing road.

Retain every claim with provenance until evidence **classifies** it. Do not treat unproven claims as true. Do not discard them as false.

### Hard rules (must be machine-enforceable)

| Rule | Meaning |
|------|---------|
| Not a soft server | Do not optimize for comfort, consensus, narrative, reputation, or a neat total. |
| Source ≠ proof | An agent, registry, model, official, majority, Gameworld display, or prior Observer conclusion is a **claim or input**, not automatic proof. |
| Preserve, don't erase | Unverified / disputed / contradicted / inconvenient information is kept with its evidence state. Corrections are append-only. |
| `PROVEN_FALSE` / `DISPROVEN` | Requires a documented determination path. Failed search, disagreement, official denial, model refusal, or unpopularity is not enough. |
| `VERIFIED` | Requires provenance + an actual test of the claim. No decorative labels. |
| Examiner is adversarial | Investigator cannot force Examiner agreement. Unresolved contradiction blocks certainty. |
| Consensus ≠ proof | N agents / majority / official / repetition / ten copies of one origin ≠ independent corroboration. |
| Model output ≠ evidence | Hypothesis / lead / interpretation only, until independently established. |
| Search failures are distinct | `NOT FOUND` ≠ `NOT SEARCHED` ≠ `SOURCE UNAVAILABLE` ≠ `PROVEN_FALSE`. |
| Comprehensive totals | “How many / everything / complete” must build an incident ledger or say a complete total cannot be established — never five headlines as the picture. |
| Source universe | No approved-news whitelist. YouTube, GitHub, courts, archives, Freenet/I2P/Tor **as source classes** are eligible. Searchable ≠ truthful. |
| Lawful public access | Observe / preserve / cite public sources. Do not steal credentials, pwn systems, or give operational crime instructions. |
| Self-reportable | Observer, methods, errors, blind spots, creator assertions, and corrections are themselves evidence subjects. |
| Inquiry search frame | Every investigation searches **who / what / when / where / possible how / possible why**. How and why stay POSSIBLE until a mechanism is independently established. |

Seated vs missing for this amendment is in `docs/OBSERVER_EPISTEMIC_INTEGRITY_AUDIT.md`. Live Freenet/I2P/Tor **adapters** remain **UNAVAILABLE** until a real adapter is proven. The **source-network types** exist so “not searched” is honest.
