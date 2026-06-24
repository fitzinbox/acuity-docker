# ANewAcuity

ANewAcuity is a modernised fork of [ACUITY](https://github.com/digital-cancer-research), an open-source clinical trial data visualisation platform. It presents patient-level data — adverse events, laboratory results, tumour response (RECIST), pharmacokinetics, dosing timelines, vital signs, ECGs, and more — as interactive charts and tables for clinical researchers and data scientists.

This repository (`acuity-docker`) is the entry point for running the full stack via Docker Compose.

## What's different from upstream ACUITY

- **Security removed** — the VASecurity authentication service is not required. All data is open-access. Add your own authentication layer (e.g. an nginx auth proxy) if needed for your deployment.
- **Fully modernised stack** — Java 21, Spring Boot 3.3.5, Angular 19, PostgreSQL 16. Upstream ran Java 8, Spring Boot 1.5, Angular 5, PostgreSQL 11.
- **PostgreSQL only** — all Oracle-specific SQL replaced with standard PostgreSQL.
- **Community ag-Grid** — Enterprise licence dependency removed.

## Prerequisites

| Tool | Version |
|------|---------|
| Docker | 24+ (with Docker Compose v2) |
| Java | 21 (for building from source) |
| Maven | 3.8+ (for building from source) |
| Node.js | 18.x via nvm (for frontend builds) |

If you only want to **run** the stack (not build from source), Docker is all you need — the build artefacts are copied into `building-mode/builds/` before the containers start.

## Quick start

```bash
# Clone all repos (see Repository structure below)
git clone https://github.com/fitzinbox/acuity-docker
# ... clone remaining repos into the same parent directory

# First run — wipe and initialise the database
cd acuity-docker
docker compose -f docker-compose_building-mode.yml --env-file .env.dev --profile main down -v
docker compose -f docker-compose_building-mode.yml --env-file .env.dev --profile main up -d

# Subsequent runs
docker compose -f docker-compose_building-mode.yml --env-file .env.dev --profile main up -d
```

Once running:
- **VAHub** (visualisation UI): http://localhost:8080
- **AdminUI** (data loading): http://localhost:8081
- **Health check**: http://localhost:8080/actuator/health → `{"status":"UP"}`

Startup takes 3–5 minutes. AdminUI logs to `/var/log/adminui/adminui.log` inside the container (not stdout).

## Repository structure

All repositories should be cloned into the same parent directory.

| Repo | Role |
|------|------|
| `acuity-docker` | Docker Compose orchestration — **start here** |
| `acuity-vahub` | Main app — Spring Boot backend + Angular 19 frontend |
| `acuity-admin` | Data loading — Spring Boot + Spring Batch ETL |
| `acuity-config-server` | Spring Cloud Config Server |
| `acuity-flyway` | Flyway database migrations |
| `acuity-va-security` | Auth library (build and install locally; not a running service) |
| `acuity-deployment-scripts` | Azure provisioning scripts (optional) |
| `ACUITY_docs` | Documentation |

All repos are on the `main` branch.

## Building from source

See [TECHNICAL_GUIDE.md](https://github.com/fitzinbox/acuity-vahub/blob/main/TECHNICAL_GUIDE.md) for full build instructions. The short version:

```bash
# 1. Build va-security library first
cd acuity-va-security
mvn clean install -Dmaven.test.skip=true -Dfindbugs.skip=true

# 2. Build vahub (backend + Angular frontend)
cd acuity-vahub
mvn clean package -Pwebapp -Dmaven.test.skip=true -Dfindbugs.skip=true -Dcheckstyle.skip=true

# 3. Build adminui
cd acuity-admin
mvn clean package -Dmaven.test.skip=true -Dfindbugs.skip=true -Dcheckstyle.skip=true

# 4. Copy build artefacts
cp acuity-vahub/vahub/target/vahub-9.0-beryllium-SNAPSHOT.war  acuity-docker/building-mode/builds/vahub.war
cp acuity-admin/acuity-core/target/adminui-9.0-beryllium-SNAPSHOT.war acuity-docker/building-mode/builds/adminui.war
```

## Loading data

Data is loaded via AdminUI using SDTM-format CSV files. The process is:

1. Create a **Drug Programme** and **Dataset** in AdminUI
2. Map each SDTM domain file to the corresponding entity (AE, LB, VS, EG, EX, PC, TR, CM, MH, DM, DS, etc.)
3. Run the ETL job

A data loading walkthrough will be added in a future release.

## Configuration

Spring configuration files live in `acuity-spring-configs/`. Database credentials and service passwords are set via environment files in `env-configs/`.

> **Important:** The default database password (`POSTGRES_PASSWORD=1`) and Spring inter-service credentials (`username`/`pass`) are development defaults only. Override these for any non-local or shared deployment.

## Known limitations

- **No authentication** — all data is accessible to anyone who can reach the application. Secure your network perimeter accordingly.
- **14 pre-existing test failures** in `vahub-model` (AeChordContributor, AeService, TumourColumnRange) — domain logic assertion mismatches, not build-blocking.
- **ag-Grid Community only** — Enterprise features (column grouping menus, row grouping) are not available.
- **va-security Maven dependency** — vahub and adminui still reference va-security as a compile-time library. Full removal is planned for a future release.

## Contributing

Open an issue or pull request on GitHub.

## Licence

Apache 2.0 — see [LICENSE](LICENSE). Forked from [digital-cancer-research/ACUITY](https://github.com/digital-cancer-research) which is also Apache 2.0.
