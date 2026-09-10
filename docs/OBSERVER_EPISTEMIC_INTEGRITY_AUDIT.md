# OBSERVER EPISTEMIC INTEGRITY AUDIT

Written **2026-09-01**. Observer-only. Federation expansion **not** started. Aster Acceptance Test **not** changed.

Command: `python -m pytest tests -q` in `D:\The_Observer`  
Result: **128 passed** (Hermes venv, 2026-09-01). Prior suite was **122**.

## Files inspected

`CHARTER.md`, `docs/SPEC.md`, `observer/core.py`, `observer/models.py`, `observer/policy.py`, `observer/contradictions.py`, `observer/hypotheses.py`, `observer/ledger.py`, `observer/reports.py`, `observer/sources.py`, `observer/audit.py`, `observer/pipeline.py`, `observer/registry.py`, `observer/salvage.py`, `observer/identity` (`observer/__init__.py`), `observer/research/web_search.py`, `observer/research/base.py`.

## Files changed

| Path | Change |
|------|--------|
| `docs/SPEC.md` | Complete Observer **build** amendment — architectural requirement |
| `CHARTER.md` | Hard epistemic / source-universe / self-report law |
| `docs/OBSERVER_EPISTEMIC_STANDARD.md` | Canonical detailed standard (one law, not competing copies) |
| `docs/OBSERVER_EPISTEMIC_INTEGRITY_AUDIT.md` | This report |
| `README.md` | Pointer to standard |
| `observer/core.py` | Claim statuses + `MODEL_GENERATED` |
| `observer/models.py` | Append-only history, examiner findings, error/blind-spot/access-failure tables |
| `observer/epistemic.py` | **New** — promotion gates, comprehensive totals, civil-incident classification |
| `observer/source_universe.py` | **New** — source classes/networks, discovery vs evidence, copy groups |
| `observer/reports.py` | `we_report_what_we_find` |
| `observer/registry.py` | `epistemic_integrity` / `source_universe` CONNECTED; Freenet/I2P/Tor/IPFS adapters UNAVAILABLE; `observer_creator` no-immunity |
| `observer/__init__.py` | `soft_server` / `news_summarizer` in `not` |
| `tests/test_epistemic.py` | Refusal-to-lie suite |
| `tests/test_source_universe.py` | Source-universe suite |
| `tests/test_identity.py` | soft_server |

**Follow-up 2026-09-01 (inquiry search):** `observer/epistemic.py` inquiry frame; `observer/questions.py` INQUIRY/PLACE/MECHANISM/MOTIVE; `observer/reports.py` `inquiry`; `observer/graph.py` POSSIBLE_HOW/WHY; `tests/test_inquiry.py`; dashboard inquiry section. Pytest **128**.

Did **not** modify `federation/` (Living Home). Did **not** change `D:\Court\federation\ASTER_ACCEPTANCE.json`. Did **not** connect unavailable reviewers. Did **not** restart the live `:8730` process merely to green a test.

## Already compliant (before this pass)

| Requirement | Status | Evidence |
|-------------|--------|----------|
| FACT/ANALYSIS/HYPOTHESIS labels | PASS | `EpistemicKind`, reports |
| Same-publisher ≠ independent corroboration | PASS | `ledger._refresh_corroboration`, tests |
| Contradictions recorded, not judged | PASS | `contradictions.scan_investigation` |
| Examiner 12-question audit | PASS | `audit.adversarial_review` |
| Default conclusion insufficient evidence | PASS | `reports.build_report` |
| Append-only conclusions | PASS | `hypotheses.append_conclusion` versions |
| Public intake UNREVIEWED | PASS | `public.submit` |
| No fabricated reviewers | PASS | `four_reviewers` UNAVAILABLE |
| No auth/paywall bypass | PASS | `policy.assess_fetch_url` |
| Observer on no-immunity list | PASS | `the_observer` category |
| Federation does not own family | PASS | existing desk; out of scope here |

## This pass

| Requirement | Status | Notes |
|-------------|--------|-------|
| Fact-finder / not soft server (law) | PASS | Charter + SPEC + standard |
| Unverified ↛ VERIFIED | PASS | `may_promote` + tests |
| No evidence ↛ FALSE / DISPROVEN | PASS | `INSUFFICIENT_EVIDENCE` |
| Copies ↛ independent corroboration | PASS | independence groups + promotion gate |
| Official denial ↛ disproof | PASS | |
| Fringe ↛ auto-false | PASS | |
| Model output ↛ evidence | PASS | `MODEL_GENERATED` |
| Contradiction preserved | PASS | existing engine + VERIFIED blocked if unresolved |
| Correction keeps history | PASS | `claim_status_history` |
| DISPROVEN needs determination path | PASS | |
| Examiner can disagree; Investigator cannot force | PASS | `examiner_findings` |
| User video = LEAD until authenticated | PASS | classifier (no forensic auth pipeline) |
| Prestige / politics / popularity ↛ weight | PASS | explicit non-weighting |
| Peaceful protest ↛ riot; ordinary crime ↛ unrest | PASS | `classify_civil_incident` |
| Old article ↛ ACTIVE | PASS | `event_temporal_state` |
| Comprehensive ≠ five headlines | PASS | `complete_total_report` |
| Inquiry who/what/when/where + possible how/why | PASS | `build_inquiry_frame`; how/why cannot be FACT by assertion |
| Mainstream-only insufficient for comprehensive | PASS | |
| Source universe (YouTube, GitHub, Freenet types, …) | PASS | types + classifiers |
| News whitelist forbidden | PASS | `refuse_news_only_gate` |
| Discovery ≠ evidence source | PASS | |
| Access failure ↛ false | PASS | |
| Error / blind-spot ledgers | PASS | tables + functions |
| Operational crime assistance | PASS | refused |
| Creator on no-immunity list | PASS | `observer_creator` |
| Live Freenet/I2P/Tor/IPFS fetch | MISSING | adapters **UNAVAILABLE**; honest `NOT SEARCHED` |
| Pipeline auto-calls `promote_claim` on ingest | PARTIAL | ingest still starts UNVERIFIED (correct); promotion is explicit |
| Live comprehensive unrest collector | MISSING | rules seated; no national incident crawler |
| Research-reproduction UI | MISSING | schema/report flags only |
| Periodic self-audit job | PARTIAL | ledgers exist; no scheduled “what are we getting wrong?” run |
| C2PA / video authentication | MISSING | LEAD/EVIDENCE split only |

## Remaining gaps (do not claim seated)

1. Live fetch of Freenet / I2P / Tor / IPFS — **do not fake CONNECTED**.
2. Production investigation `pipeline.run` does not yet emit comprehensive incident ledgers for “how many” questions — the **gate** refuses headline substitution when that reporter is used; the crawler is not built.
3. Existing live SQLite at `:8730` gains new tables on next `init_db` / Observer restart. Tests used a fresh DB. Restart is **not** federation expansion; it is optional for the new tables to appear in the running desk.
4. Inquiry frame is seated in reports/questions; live DuckDuckGo still searches the original question (plan recorded; extra per-slot fetches not fired this pass).

## Federation boundary (held)

```text
EXPANSION STATUS: PAUSED
```

Full Aster Acceptance Test remains whatever `D:\Court\federation\ASTER_ACCEPTANCE.json` already records (`overall: FAIL`; live negatives still open). This amendment does not touch that file.

## Exact commands

```text
cd D:\The_Observer
python -m pytest tests -q
```
