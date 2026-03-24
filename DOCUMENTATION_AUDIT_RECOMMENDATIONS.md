# Documentation Audit — requirements.md & AGENTS.md

**Date:** 2026-03-19  
**Auditor:** Cascade  
**Status:** Awaiting Approval

---

## Executive Summary

Both `memory-bank/requirements.md` and `AGENTS.md` contain **outdated project naming** and **minor inconsistencies** with the current codebase state. The core technical content is accurate, but several references need updating to reflect:

1. **Project rename:** `Reachy_Local_08.4.2` → `Reachy_EQ_PPE_Degree_Mini_01`
2. **React marketing website:** Not documented in either file
3. **Phase 2 completion status:** 95% complete (not reflected in milestones)
4. **Version alignment:** requirements.md is at v0.09.2, AGENTS.md still references v08.4.2

---

## Critical Findings

### 1. Project Name Inconsistency

**Issue:** Multiple naming conventions used across documentation and codebase.

**Current State:**
- `AGENTS.md` header: "Reachy_Local_08.4.2"
- `requirements.md` header: "Reachy_EQ_PPE_Degree_Mini_01" (v0.09.2)
- `README.md` header: "Reachy_Local_08.4.2"
- Codebase grep: 129 matches across 69 files with mixed naming

**Recommendation:**
- **Standardize on:** `Reachy_EQ_PPE_Degree_Mini_01` (matches requirements.md v0.09.2)
- Update `AGENTS.md` line 1 from "Reachy_Local_08.4.2" to "Reachy_EQ_PPE_Degree_Mini_01"
- Update `README.md` line 1 from "Reachy_Local_08.4.2" to "Reachy_EQ_PPE_Degree_Mini_01"
- Update AGENTS.md line 30 reference to `requirements_08.4.2.md` → `requirements.md`
- Update AGENTS.md line 277 reference to `Agents_08.4.2.md` → `AGENTS.md`

**Justification:** Version 0.09.2 (2026-03-13) is the latest and includes Phase 2 Emotional Intelligence Layer completion.

---

### 2. React Marketing Website Not Documented

**Issue:** The React marketing website (`apps/web/dev/`) is a significant deliverable but not mentioned in either requirements.md or AGENTS.md.

**Current State:**
- React website exists at `apps/web/dev/` with 7 pages, production-ready
- Deployed to GitHub Pages at `https://rustybee2016.github.io/project-reachy-emotion/`
- Built with React 18.3 + Vite 5.4 + TailwindCSS 3.4
- No documentation in requirements.md §2 (Project Scope) or AGENTS.md

**Recommendation:**
Add new section to `requirements.md` after §2.1:

```markdown
### 2.1.1 Marketing Website
- **React-based marketing site** (`apps/web/dev/`) deployed to GitHub Pages
- **Purpose:** Public-facing documentation, architecture diagrams, privacy policy, use cases
- **Stack:** React 18.3, Vite 5.4, TailwindCSS 3.4, React Router 6.26, Lucide icons
- **Pages:** Home, Technology, Architecture, Privacy & Safety, Use Cases, About, Contact
- **Deployment:** Automated via `gh-pages` package to `https://rustybee2016.github.io/project-reachy-emotion/`
- **Key Components:** EQ gauge visualization, gesture modulation showcase, animated backgrounds
```

**Justification:** The React website is a production deliverable that demonstrates the project's capabilities and should be documented alongside the Streamlit web app.

---

### 3. Phase 2 Completion Status Mismatch

**Issue:** Phase 2 is documented as 95% complete in version history but not reflected in milestones or status sections.

**Current State:**
- `requirements.md` line 30: "Phase 2 Emotional Intelligence Layer 95% complete"
- `requirements.md` §10 (Timeline): All milestones show "Not Started" or "In Progress"
- `README.md` line 34: "Phase 2: Emotional Intelligence Layer — 95% Complete"

**Recommendation:**
Update `requirements.md` §10 (Timeline and Milestones):

```markdown
| Milestone | Target Date | Owner | Status |
|-----------|-------------|-------|--------|
| Requirements Finalized | 2025-10-01 | Russell Bray | ✅ Complete |
| Phase 1: Offline ML System | 2025-12-31 | Russell Bray | ✅ Complete |
| Phase 2: Emotional Intelligence | 2026-02-15 | Russell Bray | ✅ 95% Complete |
| Phase 3: Edge Deployment | 2026-05-10 | Russell Bray | ⏳ In Progress |
| Production Release | 2026-06-30 | Russell Bray | Pending |
```

**Justification:** Aligns milestones with actual project progress documented in version history and README.

---

### 4. Web App Pages Not Listed

**Issue:** requirements.md mentions "web app" but doesn't enumerate the 10 Streamlit pages now available.

**Current State:**
- 10 Streamlit pages exist in `apps/web/pages/`
- Only generic "web app" mentioned in requirements.md §5.1
- No mention of advanced pages: Fine_Tune (07), Compare (08), EQ_Calibration (09)

**Recommendation:**
Add detailed web app inventory to `requirements.md` §5.1 after FR-005:

```markdown
### 5.1.1 Web Application Pages (Streamlit)
- **00_Home.py** — System dashboard with status and quick links
- **01_Generate.py** — Synthetic video generation (Luma/Runway API)
- **02_Label.py** — Human-in-the-loop labeling with class balance tracking
- **03_Train.py** — EfficientNet-B0 training launch with hyperparameter controls
- **04_Deploy.py** — TensorRT engine deployment to Jetson
- **05_Video_Management.py** — Video library browser with promotion/deletion
- **06_Dashboard.py** — Gate A metrics dashboard (F1, ECE, Brier, confusion matrices)
- **07_Fine_Tune.py** — Variant 2 fine-tuning with 25+ tuneable hyperparameters
- **08_Compare.py** — Direct model comparison (Base vs Variant 1 vs Variant 2)
- **09_EQ_Calibration.py** — EQ calibration metrics (ECE, Brier, MCE)
```

**Justification:** Documents the complete web app surface area, especially advanced ML pages (07-09) that support Phase 2 objectives.

---

### 5. n8n Workflow Version Reference

**Issue:** AGENTS.md references workflow paths but doesn't clarify that v.2 is the production version.

**Current State:**
- AGENTS.md lines 133, 150, 168 reference `ml-agentic-ai_v.2/` workflows
- No statement that v.2 is production-ready and v.1 is deprecated
- `PROJECT_FILES_INVENTORY.md` confirms v.2 is production, v.1 is legacy

**Recommendation:**
Add clarification to AGENTS.md §61 (Agent Overview):

```markdown
## Agent Overview
The Reachy_EQ_PPE_Degree_Mini_01 system uses **ten cooperating agents**, each performing one narrow, auditable task in the video → label → train → evaluate → deploy loop.  
All orchestration occurs in **n8n** running on Ubuntu 1.

**Workflow Versions:**
- **Production:** `n8n/workflows/ml-agentic-ai_v.2/` (EfficientNet-B0, 3-class, 10 agents)
- **Legacy:** `n8n/workflows/ml-agentic-ai_v.1/` (ResNet-50, deprecated per ADR 006)
```

**Justification:** Clarifies which workflows are active and prevents confusion when browsing the repository.

---

### 6. Minor Technical Corrections

**Issue:** Small technical inaccuracies in descriptions.

**Findings:**

1. **requirements.md line 318:** "EfficientNet-B0 EmotionNet `.engine`" — should be "EfficientNet-B0 `.engine`" (EmotionNet is deprecated)
2. **requirements.md line 335:** "TAO retraining" — should be "PyTorch retraining" (TAO is legacy, see ADR 006)
3. **AGENTS.md line 237:** "Follow OpenAI and NVIDIA TAO usage policies" — TAO reference is outdated

**Recommendation:**

**requirements.md line 318:**
```markdown
- **Jetson (Reachy edge device)**  
  DeepStream + TensorRT (`gst-nvinfer`) loading EfficientNet-B0 `.engine`; emits JSON (no raw video); consumes cues over WebSocket.
```

**requirements.md line 335:**
```markdown
8. PyTorch retraining; new TRT engine versioned/signed; packaged for DeepStream `nvinfer`.
```

**AGENTS.md line 237:**
```markdown
- Follow OpenAI API usage policies; maintain local-only data flows.  
```

**Justification:** Removes references to deprecated TAO toolchain (superseded by PyTorch + timm per ADR 006).

---

### 7. Success Metrics Update

**Issue:** Gateway API test count may be outdated.

**Current State:**
- `requirements.md` line 60: "Gateway API regression suite: **59/59 tests passing** (validated 2025-11-26)"
- Date is 4 months old (now 2026-03-19)

**Recommendation:**
Either:
1. Re-run test suite and update count + date, OR
2. Remove specific count and use generic statement:

```markdown
- Gateway API regression suite: All tests passing (validated 2026-03-19)
```

**Justification:** Specific test counts become stale quickly; generic "all passing" is more maintainable.

---

## Non-Critical Observations

### 1. Documentation Cross-References
- AGENTS.md line 257 references `memory-bank/requirements.md` ✅ Correct
- AGENTS.md line 277 references `requirements_08.4.2.md` ❌ Should be `memory-bank/requirements.md`

### 2. File Naming Consistency
- Current: `AGENTS.md` (root), `requirements.md` (memory-bank/)
- Both are correct locations per memory-bank index

### 3. Version History Completeness
- requirements.md has comprehensive version history through v0.09.2 ✅
- AGENTS.md has no version history section (acceptable for agent specs)

---

## Recommended Update Priority

### High Priority (Breaking/Confusing)
1. ✅ **Project name standardization** (AGENTS.md, README.md)
2. ✅ **TAO → PyTorch corrections** (requirements.md, AGENTS.md)
3. ✅ **Phase 2 milestone status** (requirements.md §10)

### Medium Priority (Missing Documentation)
4. ✅ **React website documentation** (requirements.md §2.1.1)
5. ✅ **Web app page inventory** (requirements.md §5.1.1)
6. ✅ **n8n workflow version clarification** (AGENTS.md §61)

### Low Priority (Maintenance)
7. ⏳ **Success metrics update** (requirements.md §1, optional)
8. ⏳ **Cross-reference cleanup** (AGENTS.md line 277)

---

## Proposed Changes Summary

### AGENTS.md (8 changes)
1. Line 1: `Reachy_Local_08.4.2` → `Reachy_EQ_PPE_Degree_Mini_01`
2. Line 30: `requirements_08.4.2.md` → `memory-bank/requirements.md`
3. Line 61-63: Add workflow version clarification
4. Line 237: Remove TAO reference
5. Line 277: `Agents_08.4.2.md` → `AGENTS.md`
6. Line 277: `requirements_08.4.2.md` → `memory-bank/requirements.md`

### requirements.md (5 changes)
1. After §2.1: Add §2.1.1 Marketing Website
2. After §5.1 FR-005: Add §5.1.1 Web Application Pages
3. §10: Update milestone statuses
4. Line 318: Remove "EmotionNet" from Jetson description
5. Line 335: "TAO retraining" → "PyTorch retraining"

### README.md (1 change)
1. Line 1: `Reachy_Local_08.4.2` → `Reachy_EQ_PPE_Degree_Mini_01`

---

## Validation Checklist

After updates, verify:
- [ ] All project name references use `Reachy_EQ_PPE_Degree_Mini_01`
- [ ] No references to deprecated TAO toolchain (except in version history)
- [ ] React website documented in requirements.md
- [ ] Web app pages enumerated in requirements.md
- [ ] Phase 2 milestone marked 95% complete
- [ ] n8n workflow versions clarified
- [ ] Cross-references point to correct file paths

---

## Conclusion

**Overall Assessment:** Both documents are **substantially accurate** but require **naming standardization** and **minor updates** to reflect:
- Current project name (v0.09.2)
- React website deliverable
- Phase 2 completion status
- PyTorch-based training stack (post-TAO deprecation)

**Recommendation:** Approve all High + Medium priority changes. Low priority changes are optional maintenance items.

**Estimated Update Time:** 15-20 minutes for all changes.

---

**Awaiting your approval to proceed with updates.**
