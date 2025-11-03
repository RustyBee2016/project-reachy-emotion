# Updated requirements_08.4.2.md

**User:** Anonymous (rustybee255@gmail.com)  
**Created:** 10/19/2025 12:26:16  
**Updated:** 10/21/2025 19:22:05  
**Exported:** 10/21/2025 19:23:38  
**Link:** [https://chatgpt.com/g/g-p-687d178cc6b481919c71aa820f0163ba-reachy-app/c/68f51127-8690-8326-a6b3-f16d32ccf0c7](https://chatgpt.com/g/g-p-687d178cc6b481919c71aa820f0163ba-reachy-app/c/68f51127-8690-8326-a6b3-f16d32ccf0c7)  

## Response:
Thought for 22s

Short answer: fold the Pydantic v2 migration into the **requirements** as first-class policy. Don’t hide it as an implementation detail. Make it explicit how models are defined, validated, and serialized, and what that means for client contracts, tests, and CI.

Here’s the update I recommend (drop-in text you can paste into `requirements_08.4.2.md`).

* * *

Patch: requirements\_08.4.2.md — API & Data Model updates (Pydantic v2)
=======================================================================

8.1 Runtime & Framework Pins (replaces current table row if present)
--------------------------------------------------------------------

*   **Python**: 3.11 (backend services).  
    _Rationale:_ faster startup/GC, better typing/perf with Pydantic v2. (Jetson runtime for DeepStream may remain on 3.8/3.10 if vendor constraints apply.)
*   **FastAPI**: ≥ 0.111 (Pydantic v2 native)
*   **Pydantic**: ≥ 2.7 + **pydantic-settings** ≥ 2.3
*   **SQLAlchemy**: 2.0.x, **Alembic**: ≥ 1.13
*   **Uvicorn**: ≥ 0.29
*   **Starlette**: ≥ 0.37

11\. Data Storage & Workflow (add subsection)
---------------------------------------------

### 11.4 Configuration & Secrets (Pydantic v2)

*   All service configuration is defined with **pydantic-settings** v2 (env-first).
*   Required variables are **typed** and **strict**. Missing/invalid values fail boot.
*   `.env` is for local dev only. Commit `.env.example` with docs and defaults; never commit real secrets.

```py
# app/core/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyUrl, field_validator

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: AnyUrl
    JWT_SECRET: str
    ALLOWED_ORIGINS: list[str] = ["https://10.0.4.130"]

    @field_validator("JWT_SECRET")
    @classmethod
    def strong_secret(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("JWT_SECRET too short")
        return v

settings = Settings()
```

### 11.5 API Models & Contracts (Pydantic v2)

*   **All request/response DTOs** are Pydantic v2 `BaseModel` with:
    *   `model_config = {"from_attributes": True, "populate_by_name": True}`
    *   **Strict types** for ids, enums, and timestamps.
    *   **Aliases** stabilized for backwards compatibility (no breaking rename without deprecation).
*   **Validation** uses `@field_validator` / `@model_validator` (no `@validator`) and `TypeAdapter` for custom parsing when needed.
*   **Serialization** is **opt-in** via `.model_dump() / .model_dump_json()` only; no `dict()`/`json()` helpers.

```py
# app/schemas/video.py
from enum import StrEnum
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

class Emotion(StrEnum):
    happy = "happy"
    sad = "sad"

class VideoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    id: int
    sha256: str
    split: StrEnum = Field(..., alias="dataset_split")  # alias stabilized
    label: Emotion | None = None                       # test = None
    duration_sec: float = Field(gt=0)
    fps: float = Field(gt=0)
    href: str  # Nginx static URL
    created_at: datetime

# Example custom coercion (where needed)
PositiveIntList = TypeAdapter(list[int])
```

### 11.6 Error Envelope (stabilized)

All API errors (4xx/5xx) return a uniform envelope:

```json
{
  "error": {
    "code": "string-snake-case",
    "message": "human readable summary",
    "details": {...},        // optional, stable keys
    "correlation_id": "uuid" // echoed from request/response headers
  }
}
```

**Never** return raw Pydantic validation payloads. Map them to `validation_error` with field paths.

### 11.7 OpenAPI & Versioning

*   **OpenAPI** is generated on build and committed under `apps/api/openapi.json` to enable **spec diffs** in CI.
*   **API versioning**: `v1` path prefix is reserved for future; current API remains unprefixed but must carry `X-API-Version: 0.1` header in responses.
*   Any **breaking change** requires a new minor _doc_ version and a deprecation window (see §15).

12\. Quality Gates — API (new)
------------------------------

To count as “ready for integration”:

1.  **Schema Snapshots:** OpenAPI diff vs. main has **no breaking changes** (endpoint removals, response shape/required field changes).
2.  **Pydantic Strictness:** All DTOs use strict types; adding `typing.Annotated[..., Strict=True]` where ambiguity is risky.
3.  **Negative Tests:** For each endpoint, at least one failing request proves validators/guards.
4.  **Performance:** p50 ≤ 10ms, p95 ≤ 30ms for pure‐DTO handlers (`/healthz`, `/stats`) measured locally.
5.  **DB↔DTO Fidelity:** `from_attributes=True` path for ORM objects has parity with `SELECT` queries (no missing fields).

13\. CI/CD (amend)
------------------

*   Add **OpenAPI contract check**:
    *   Generate `openapi.json` on CI; run **oas-diff** against the baseline. Fail on breaking changes.
*   Add **mypy** strictness for schemas (`disallow_any_generics = true`, `warn_redundant_casts = true`).
*   Add **pytest** suite for validation errors (snapshots of `error.code`, stable `details` schema).
*   Gate merges on **ruff**, **mypy**, **pytest**, **oas-diff**.

```yaml
# .github/workflows/ci.yml (excerpt)
- name: Build OpenAPI
  run: uvicorn app.main:app --port 0 --reload --loop asyncio & sleep 2 && curl -sS http://127.0.0.1:8000/openapi.json > openapi.json
- name: OpenAPI Diff
  uses: char0n/oasdiff-action@v3
  with:
    base: ./openapi-baseline.json
    revision: ./openapi.json
    fail-on: breaking-changes
```

14\. Backwards Compatibility & Deprecations (new)
-------------------------------------------------

*   **No silent field renames.** Use aliases and keep both names for ≥ 1 minor release.
*   **Deprecated fields** are annotated in OpenAPI `deprecated: true` and removed after the window closes.
*   **Clients** must ignore unknown fields; servers must ignore unknown request fields (unless unsafe).
*   **Error codes** are stable; adding new codes is non-breaking.

15\. Service Conventions (clarify)
----------------------------------

*   **root\_path** remains `/api/media` (behind Nginx). Health endpoints:
    *   `GET /api/media/healthz` → `{ "status": "ok" }`
*   **Static URLs** continue to be served by Nginx (`/videos/...`, `/thumbs/...`); API returns **hrefs** only, never file bytes.

16\. Migration Notes (v1 → v2 models) (new appendix)
----------------------------------------------------

*   Replaced `@validator` → `@field_validator` / `@model_validator`.
*   Replaced `.dict()`/`.json()` → `.model_dump()` / `.model_dump_json()`.
*   Introduced `TypeAdapter` where ad-hoc parsing was used.
*   Config moved from inner `class Config` → `model_config`.
*   `from_orm=True` replaced by `from_attributes=True`.
*   Settings now use **pydantic-settings**; `BaseSettings` from pydantic v1 is not used.

17\. Test Matrix (extend)
-------------------------

*   **Unit**: DTO validators (happy path + failure cases).
*   **Contract**: OpenAPI snapshot + error codes.
*   **Integration**: ORM → DTO `from_attributes` path for `video`, `promotion_log`.
*   **Perf**: JSON (de)serialization micro-benchmarks for hot DTOs (`VideoOut`, `LabelIn`, etc.).

* * *

Why this matters for the rest of the doc (what it implicitly fixes)
-------------------------------------------------------------------

*   **Functional Requirements (FR-002/003/004)**: promotion & balance logic returns stable, typed payloads to the UI; “test = no label” is enforced by DTO + DB constraints, and errors are predictable via the new envelope.
*   **Agents file alignment**: Ingest/Label/Promotion agents can rely on strict DTOs and error codes; training/eval agents get stable manifests produced by serializers, not ad-hoc dicts.
*   **Nginx + root\_path**: the `root_path="/api/media"` contract is now codified; clients should never hardcode raw filesystem paths.
*   **Future work (SQLAlchemy 2)**: `from_attributes=True` removes the lingering “from\_orm” v1 pattern and aligns with your 2.0-style ORM usage.

* * *

### If you want the super-short checklist to mark this “Done”:

*    Bump runtime pins (Python 3.11, FastAPI ≥ 0.111, Pydantic ≥ 2.7).
*    Move settings to `pydantic-settings` v2.
*    Replace all v1 validators/Config and dumps with v2 equivalents.
*    Add error envelope mapper + OpenAPI snapshot to CI.
*    Stabilize/alias any renamed fields; mark deprecations.
*    Merge once oas-diff shows **no breaking changes**.

You’ve already done the hard part (the code migration). The doc change just makes it a **project promise**, so future edits don’t quietly drift.



---
Powered by [ChatGPT Exporter](https://www.chatgptexporter.com)