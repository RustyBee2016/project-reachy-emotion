# ReachyOps AI — Site Architecture Blueprint

**Last Updated**: 2026-03-25
**Domain**: https://affective-ai.io
**Hosting**: GitHub Pages (gh-pages branch, HashRouter)
**Stack**: React 18.3 + Vite 5.4 + TailwindCSS 3.4 + Lucide Icons

---

## Umbrella Brand

**ReachyOps AI** — A governed physical-AI operations platform with Reachy as the embodied user-experience layer.

**Tagline**: *Governed Physical AI for Enterprise Operations*

---

## Site Map (13 routes)

| Route | Page | Purpose |
|---|---|---|
| `/` | HomePage | ReachyOps AI platform landing — umbrella positioning |
| `/platform` | PlatformPage | Shared architecture: Jetson + workstation + Postgres + n8n + Reachy |
| `/careflow` | CareFlowPage | Healthcare operations vertical — full flagship page |
| `/secureflow` | SecureFlowPage | Cybersecurity / secure facilities vertical — full flagship page |
| `/technology` | TechnologyPage | EfficientNet-B0, HSEmotion, DeepStream/TensorRT (existing, retained) |
| `/architecture` | ArchitecturePage | Three-node system, 10-agent orchestration (existing, retained) |
| `/governance` | GovernancePage | Governance matrix, approval gates, compliance for both verticals |
| `/privacy` | PrivacySafetyPage | Privacy-by-design, GDPR (existing, retained) |
| `/dashboard` | DashboardPage | Live simulated ops dashboard (CareFlow + SecureFlow modes) |
| `/use-cases` | UseCasesPage | Expanded use cases (existing, updated) |
| `/about` | AboutPage | Russell Bray as solutions architect (updated positioning) |
| `/contact` | ContactPage | Contact form (existing, retained) |

---

## Seven Components Mapped

1. **Production-grade AI portfolio** → Platform page + Architecture page + Dashboard
2. **Map onto Reachy architecture** → Platform page (exact shared stack)
3. **Full site architecture** → All 13 routes with ML pipeline, inference, diagrams
4. **Clean production deployment** → Subroutes, dashboards, governance
5. **AI system showcase** → CareFlow + SecureFlow vertical pages
6. **Frontend structure + API endpoints** → Dashboard with simulated API data
7. **Live AI demo** → Dashboard page with animated real-time simulation

---

## Shared Architecture (Both Verticals)

### Core Stack
- **Jetson Xavier NX**: Edge perception, EfficientNet-B0 TensorRT inference
- **Ubuntu Workstation**: Control plane, FastAPI gateway, MLflow, training pipeline
- **PostgreSQL 16**: Event ledger, incidents, approvals, action history, audit
- **n8n**: Orchestration, routing, approval workflows (10 agents)
- **Reachy Mini**: Embodied communication and reassurance layer

### Shared Pattern
1. Observe (Jetson camera detection)
2. Classify (EfficientNet-B0 emotion/presence inference)
3. Generate structured event (FastAPI)
4. Evaluate policy (n8n workflow)
5. Decide allowed actions (approval gates)
6. Request approval if needed (human-in-the-loop)
7. Trigger Reachy communication (gesture + dialogue)
8. Log everything (Postgres audit trail)

---

## CareFlow Edition — Healthcare Operations

### MVP Use Cases
- **A**: Arrival detection → Reachy greets → dashboard updates → staff notified
- **B**: Wait-time threshold → Reachy reassures → escalation if exceeded
- **C**: Distress detection → high-touch flag → human attendant notified

### KPIs
- Front-desk acknowledgment time
- Queue visibility score
- Escalation response time
- Visitor reassurance score
- Staff interruption reduction

### Color Accent: `#10B981` (emerald/teal — healthcare warmth)

---

## SecureFlow Edition — Cybersecurity / Secure Facilities

### MVP Use Cases
- **A**: After-hours presence → policy check → Reachy announces → supervisor notified
- **B**: Suspicious event → operator approval required → Reachy summarizes
- **C**: Lab access anomaly → incident created → Reachy explains → no action without approval

### KPIs
- Anomaly acknowledgment time
- Review latency
- False alert handling efficiency
- Approval cycle time
- Audit completeness

### Color Accent: `#F59E0B` (amber — security alertness)

---

## Portfolio Packaging (Per Edition)

1. Business problem brief (on vertical page)
2. System architecture diagram (interactive on platform page)
3. Workflow diagram (on vertical page)
4. Demo simulation (dashboard page)
5. Governance matrix (governance page)
6. ROI / KPI section (on vertical page)
7. Executive summary (on vertical page)

---

## Navigation Structure

### Desktop Navbar
```
[Logo: ReachyOps AI]  Platform  Solutions ▾  Technology  Architecture  Governance  About  [Request Demo]
                                  ├─ CareFlow (Healthcare)
                                  └─ SecureFlow (Security)
```

### Footer
```
Platform          Solutions           Resources          Company
─────────         ─────────           ─────────          ─────────
Technology        CareFlow            Live Dashboard     About
Architecture      SecureFlow          Documentation      Contact
Governance        Platform Overview   Request Demo       GitHub
Privacy                                                  LinkedIn
```

---

## Files to Create/Modify

### New Files
- `src/pages/PlatformPage.jsx` — Shared architecture showcase
- `src/pages/CareFlowPage.jsx` — Healthcare vertical
- `src/pages/SecureFlowPage.jsx` — Security vertical
- `src/pages/GovernancePage.jsx` — Governance matrix
- `src/pages/DashboardPage.jsx` — Live simulated dashboard
- `src/components/LiveDashboard.jsx` — Reusable dashboard component

### Modified Files
- `src/App.jsx` — Add new routes
- `src/components/Navbar.jsx` — Solutions dropdown + rebranding
- `src/components/Footer.jsx` — Solutions column + rebranding
- `src/pages/HomePage.jsx` — ReachyOps AI umbrella landing
- `src/pages/AboutPage.jsx` — Solutions architect positioning

---

## Positioning Statement

> "I built a governed physical-AI operations platform and adapted it to two
> high-demand verticals: healthcare operations and secure facilities."
>
> Same platform. Different workflow logic. Different policy model.
> Different operator dashboard. Same core architecture.

---

## Session Transition Notes

If this document is being used as a handoff:
- All existing pages are preserved — no destructive changes
- New pages follow existing component patterns (Reveal, AnimatedBorderCard, G gradient text, SectionTag)
- Design system: dark theme (#080818), brand colors (pink #D4166A, purple #7B2FF7, cyan #00B4D8)
- CareFlow accent: emerald #10B981
- SecureFlow accent: amber #F59E0B
- HashRouter for GitHub Pages compatibility
- gh-pages deploy via `npm run deploy`
