# Local validation — RNA-seq trust-and-DE component

## Port map

| Service | Port |
|---------|------|
| DESeq API | 8000 |
| Contamination API | 8001 |
| Report API | 8002 |
| Orchestrator API | 8003 |

## Checklist

1. Start all four APIs with `.\start-learning-loop.ps1 -Install` or `INSTALL_DEPS=true ./start-learning-loop.sh` (see [README.md](README.md)).
2. `GET http://127.0.0.1:8003/healthz` → `ok`
3. `POST http://127.0.0.1:8003/tools/start_component` with `max_internal_cycles: 3`
4. Confirm response includes `component_summary.study.study_id` and shared inputs under `demos/_shared_studies/{study_id}/`
5. Confirm response includes `component_summary.parent_handoff.recommended_action`
6. Open portfolio page locally (`bundle exec jekyll serve`) and verify demo-mode handoff panel renders sample summary
7. Run unit tests: `PYTHONPATH=src pytest tests/ -q`
8. Optional E2E: `./verify-demo.sh` or `.\verify-demo.ps1` (requires all four APIs running)

## Expected behaviors

- **Clean contamination + DE hits** → `proceed_to_downstream`
- **Persistent contamination concern at cycle cap** → `escalate_to_parent`
- **Unstable top genes between cycles** → internal retry, then finalize with stability metrics in summary

## Parent handoff

The integration surface for a future parent orchestrator is `component_summary.json` (see `outputs/component_summary.json` for a published-site sample). Full field reference: [`COMPONENT_SUMMARY_SCHEMA.md`](COMPONENT_SUMMARY_SCHEMA.md).
