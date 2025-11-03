## Media Mover Backend Completion Checklist

- [ ] Wire `apps/api/app/routers/promote.py` to `promote_service.promote()`
  - [ ] Inject `Settings` and database session dependencies
  - [ ] Parse request payload (including `dry_run`, `label`, correlation metadata)
  - [ ] Call the promotion service and surface results
  - [ ] Translate `PromotionError` instances into structured HTTP responses
- [ ] Extend API surface for relabel and manifest workflows
  - [ ] Add relabel endpoint leveraging shared service patterns
  - [ ] Add manifest rebuild endpoint (regenerate manifests/checksums)
  - [ ] Ensure schemas and contracts match gateway expectations
- [ ] Implement regression tests (health, videos, promote)
  - [ ] Cover success paths with TestClient fixtures and temporary paths
  - [ ] Cover error handling (invalid split, missing files, DB failures)
  - [ ] Verify database and filesystem side-effects under dry-run and real moves

**Last Updated:** 2025-10-28
