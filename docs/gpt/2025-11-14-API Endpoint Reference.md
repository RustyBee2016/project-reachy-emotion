**2025-11-14-API Endpoint Reference**

**API Endpoint Reference**

\[MEMORY BANK: ACTIVE\]

Excellent request! Let me create a comprehensive endpoint reference
document for the newly rewritten system.

Perfect! I\'ve created a comprehensive API endpoint reference document.
Let me create a quick summary:

**Complete API Endpoint Reference Created**

I\'ve created **API_ENDPOINT_REFERENCE.md** - a comprehensive guide
covering all endpoints in your rewritten system.

**Document Contents**

**1. V1 API Endpoints (Production Ready)**

• Health & Monitoring (2 endpoints)

o /api/v1/health - Health check

o /api/v1/ready - Readiness check

• Media Management (3 endpoints)

o /api/v1/media/list - List videos with pagination

o /api/v1/media/{video_id} - Get video metadata

o /api/v1/media/{video_id}/thumb - Get thumbnail URL

• Video Promotion (3 endpoints)

o /api/v1/promote/stage - Stage videos to dataset

o /api/v1/promote/sample - Sample train/test splits

o /api/v1/promote/reset-manifest - Reset promotion

**2. Legacy Endpoints (Deprecated)**

• /api/videos/list - Old video listing

• /api/media/videos/list - Alternative old listing

• /api/media/promote - Old promotion (stub)

• /media/health - Old health check

• /api/media - Old media root

**3. Gateway Endpoints (External Service)**

• /api/media/ingest - Video upload

• /api/gen/request - Generation requests

• /api/privacy/redact/{video_id} - Privacy/redaction

• /api/promote - Gateway-mediated promotion

**4. Nginx Static Endpoints**

• /videos/{split}/{filename} - Video files

• /thumbs/{video_id}.jpg - Thumbnails

**Key Features**

**Complete Details** for each endpoint:

• URL and HTTP method

• Purpose and use cases

• Request/response formats

• Authentication requirements

• Query/path parameters

• Example requests (cURL, Python, JavaScript)

• Related services

• Error responses

**Quick Reference Tables**:

• Service ports

• Environment variables

• Status codes

• Common headers

**Service Dependencies**:

• Dependency graphs

• Port mappings

• Service relationships

**Migration Guide**:

• Step-by-step legacy to v1 migration

• Code examples

• Best practices

**Troubleshooting**:

• Common issues

• Solutions

• Debugging tips

**Total Endpoints Documented**

• **V1 API**: 8 endpoints (production)

• **Legacy**: 5 endpoints (deprecated)

• **Gateway**: 4 endpoints (external)

• **Nginx**: 2 endpoint patterns (static)

**Total**: 19 endpoint patterns fully documented

**Quick Access**

The document includes:

• Table of contents

• Code examples in Python, cURL, and JavaScript

• Interactive API docs links (Swagger, ReDoc)

• Cross-references to other documentation

**File Location**:
/home/rusty_admin/projects/reachy_08.4.2/API_ENDPOINT_REFERENCE.md

This comprehensive reference provides everything needed to understand
and use the rewritten endpoint system!
