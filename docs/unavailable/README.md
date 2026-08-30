# Remaining unavailable modules

Calling these must not be treated as a successful investigation step.

| Module | Status | Note |
|--------|--------|------|
| court_records | CONNECTED | CourtListener public opinions; not PACER |
| corporate_registries | CONNECTED | GLEIF LEI; not a state filing |
| sec_filings | CONNECTED | EDGAR public copies; filer statements not findings |
| patents | CONNECTED | USPTO public PDFs; a grant is not use |
| procurement | CONNECTED | USAspending awards; an award is not misconduct |
| public_submission | CONNECTED | UNREVIEWED intake only |
| four_reviewers | UNAVAILABLE | independent model reviewers not seated |
| public_fork | UNAVAILABLE | investigation forks not seated |
| malware_screen | UNAVAILABLE | upload scanning not seated |
| wayback | CONNECTED | Internet Archive snapshots |
| neo4j | not imported | NetworkX is the graph |
| postgresql | not imported | SQLite is the store |
| redis | not imported | no queue |
| faiss_qdrant | not imported | no vector index |
| ollama_extractor | unproven unless configured and tested | |
| documentary_package | none seated | cinematic/DaVinci later |
| auto_publish | DISABLED | human editor only |

A new adapter may be marked CONNECTED only after a test proves it ran.
