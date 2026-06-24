# Changelog

## v1.0.0-beryllium (2026)

First open-source release of ANewAcuity — a modernised fork of [ACUITY](https://github.com/digital-cancer-research) (upstream version 9.0-beryllium).

### Summary

ANewAcuity takes the upstream ACUITY platform and brings it forward to a fully modern technology stack, removes the proprietary VASecurity authentication service, and fixes a number of bugs in the original codebase. The clinical visualisation functionality is preserved in full.

---

### Breaking changes from upstream ACUITY

- **VASecurity removed** — the VASecurity authentication service and Azure AD integration are not present. All data is open-access. The `acuity-va-security` repository is retained as a build-only library providing shared model classes; it is not a running service.
- **PostgreSQL 16 required** — upstream supported PostgreSQL 11. All Oracle-specific SQL has been replaced with standard PostgreSQL.
- **ag-Grid Community only** — the Enterprise ag-Grid licence dependency has been removed. Enterprise-only features (column grouping menus, row grouping, context menus) are not available.

---

### Stack upgrades

| Component | Upstream | ANewAcuity |
|-----------|----------|------------|
| Java | 8 | 21 |
| Spring Boot | 1.5.4 | 3.3.5 |
| Spring Framework | 4.3.x | 6.1.x |
| Spring Batch | 3.x | 5.0.3 |
| Spring Cloud | Brixton | 2023.0.3 |
| Angular | 5 | 19.2.x |
| TypeScript | 2.6 | 5.8.3 |
| ngrx | 4 | 19 |
| ag-Grid | 12 (Enterprise) | 29 (Community) |
| PostgreSQL | 11 | 16 |
| Cache | EhCache 2.x | Caffeine |
| JAXB | javax.xml.bind | jakarta.xml.bind |
| Servlet | javax.servlet | jakarta.servlet |
| Patient summary export | docx4j 3.3.3 | docx4j 11.5.3 |

---

### Bug fixes

- **Error masking** — deleted `AcuityErrorController`, which was suppressing Spring Boot's `BasicErrorController` and returning 404 for all unhandled errors. Unknown endpoints and malformed requests now return correct HTTP status codes and JSON error bodies.
- **Box plot Details on Demand** — fixed two root causes: frontend `BoxPlotComponent.getCategories()` was returning stale categories after axis-type switches; backend `ChartSelectionItemRange` `@EqualsAndHashCode(callSuper=false)` was collapsing distinct selection items in a HashSet. Drag-selection → DoD now works correctly across all box plot tabs.
- **Oracle SQL** — removed 20+ Oracle-specific SQL calls from ETL XML and DAO files (`oracle.sysdate()`, `DECODE`, `VARCHAR2`, `ROWNUM` subquery). Fixes confirmed ETL crashes on DECODE calls in live jobs.
- **Patient summary export** — upgraded docx4j 3.3.3 → 11.5.3. The old version used `javax.xml.bind.*` which is absent from JDK 11+. `POST /resources/summary/document` now returns a valid `.docx` file.
- **Spring cache collisions** — `@EqualsAndHashCode(callSuper=true)` applied to timeline request classes, preventing cache key collisions on paginated timeline requests.
- **Lab box plot grouping** — fixed broken `Lab.equals()` causing identical box plot distributions across all groups.
- **Vitals chart visibility** — fixed "Measurements over Time" chart disappearing on measurement deselect.
- **Tumour Response filters** — added RECIST filter to TL Diameters over Time plot; fixed ASSESSMENT_TYPE 412.
- **Cross-domain test collision** — added `tst_domain` to the unique key on `RESULT_TEST.tst_visit`, preventing LB/VS/EG/ZE domain collision.

### Frontend improvements

- ag-Grid tables (DoD and SSV): sortable and resizable columns, cell text selection, tooltips, column filters, `sizeColumnsToFit()`, CSV export
- Angular 5 → 19 migration: functional guards, `standalone: false` explicit declarations, `provideHttpClient()`, SCSS migration from Stylus, `ngx-cookie-service` replacing `ngx-cookie`
- Removed springfox Swagger (incompatible with Spring Boot 3)

### Test suite

- JUnit 4 → 5 migration across 302 test files (280 vahub, 22 admin)
- Mockito 5 API updates, EhCache → Caffeine in test config, `javax.*` → `jakarta.*` in test code
- `mvn test-compile` clean across all repos

---

### Frontend dependency security audit

`npm audit` was run against the Angular frontend prior to release. 67 vulnerabilities were found in the dependency tree; 17 were resolved by safe transitive patches (`npm audit fix`, no `--force`); 50 remain deferred.

**Fixed (17) — commit `28fdd7f`:**

| Package | Severity | Issue |
|---------|----------|-------|
| loader-utils | Critical | Prototype pollution (GHSA-76p3-8jx3-jpfq), ReDoS (GHSA-3rfm-jhwj-7488, GHSA-hhq3-ff78-jv3g) |
| ws | High | Memory exhaustion DoS (GHSA-96hv-2xvq-fx4p) |
| engine.io, socket.io-adapter | High | Transitive via ws |
| http-proxy-middleware | High | CRLF injection (GHSA-gcq2-9pq2-cxqm) |
| ajv | Moderate | ReDoS via $data (GHSA-2g4f-4pwh-qvx6) |

**Deferred (50) — rationale:**

| Package(s) | Severity | Rationale |
|------------|----------|-----------|
| @angular/core, @angular/common, @angular/compiler | High/Moderate | CVEs are SSR-specific (DOM clobbering, XSS via server rendering). ANewAcuity does not use Angular SSR — these vulnerabilities have no attack surface in this application. Fix requires Angular 22+. |
| ag-grid-community | High | Prototype pollution. Fix requires ag-Grid 36 (we are on 29 — three major versions). Deferred for ag-Grid upgrade cycle. |
| babel-traverse | Critical | RCE on malicious code input — build tool only, not present at runtime. Fix would downgrade @angular/compiler-cli to v15, which would break the build. |
| lodash (in karma) | Critical | Prototype pollution and command injection — in karma-junit-reporter's subdependency only. karma is a dev-only test runner. Fix would break the karma test reporter. |
| moment | High | Path traversal, ReDoS. Pinned at `2.22.2` by upstream; upgrade to 2.30.1 deferred to assess date formatting impact. |
| d3-color / d3 | High | ReDoS. Fix requires d3 v7 major upgrade. Deferred. |
| hoek | High | Prototype pollution. No fix available — ancient transitive dependency via joi. Full dependency chain replacement needed. |
| immutable | High | Prototype pollution (GHSA-wf6x-7x77-mvgw). Pinned at `3.8.1`; upgrade to 3.8.3 is outside the version range. Low risk — immutable is used for in-memory data structures, not network input parsing. |
| bootstrap | Moderate | XSS in Popover/Tooltip components. Bootstrap 3→5 is a full CSS breaking change; deferred. |
| Build tool dependencies (tar, esbuild, vite, piscina, serialize-javascript, postcss, uuid, js-yaml, jquery) | High/Moderate | All in build tools or dev server. Fixes pull @angular-devkit/build-angular@0.802.2 (Angular CLI 8 — would break the build catastrophically). No runtime risk. |

`ng build` passes cleanly with the 17 applied patches.
