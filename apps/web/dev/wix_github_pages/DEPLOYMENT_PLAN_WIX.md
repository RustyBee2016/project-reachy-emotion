# Affective AI Website Deployment Plan: affective-ai.io via Wix

**Date:** 2026-03-11  
**Current state:** React 18 + Vite 5 + Tailwind CSS 3 SPA on localhost:5173  
**Target:** Live at https://affective-ai.io  
**Requested platform:** Wix Blocks

---

## Executive Summary

After thorough review of the Wix Blocks documentation, there is a **critical architectural mismatch** between what Wix Blocks is designed for and what we need. Wix Blocks builds *widgets/apps for Wix sites* -- it is not a general-purpose hosting platform for standalone SPAs. This document presents three options ranked by feasibility.

### Architecture Comparison

| Feature | Our React SPA | Wix Blocks |
|---|---|---|
| Framework | React 18 + Vite | Wix component system |
| Routing | React Router (7 routes) | No client-side routing |
| Styling | Tailwind CSS 3 | Wix design system |
| Animations | IntersectionObserver, Canvas | Velo code (limited) |
| DOM access | Full | Sandboxed iframe |

---

## Option A: Wix Blocks Custom Element (Requested Approach)

**Fidelity: ~85% | Complexity: HIGH | Maintenance: MEDIUM**

Wix Blocks supports Custom Elements (Web Components) inside widgets. We convert the React app into a single-file Web Component, host it on a CDN, then embed it in a Blocks widget installed on a Wix site.

### Required Code Changes

- Switch `BrowserRouter` to `HashRouter` (Wix controls the URL)
- Create `src/wix-entry.jsx` Web Component wrapper
- Add `vite.config.wix.js` library-mode build (single JS output)
- Inline all CSS into the JS bundle
- Remove any localStorage/sessionStorage usage (sandboxed)

### Step-by-Step

**Phase 1 -- Prepare React App**
1. Create Web Component wrapper (`src/wix-entry.jsx`)
2. Add Vite library-mode config (`vite.config.wix.js`)
3. Switch to HashRouter in App.jsx
4. Build single-file bundle, test locally in plain HTML

**Phase 2 -- Host the Bundle**
5. Deploy the JS bundle to Netlify (or Cloudflare Pages)
6. Verify accessible at public HTTPS URL

**Phase 3 -- Wix Blocks Setup**
7. Log into Wix Studio > Custom Apps > Create New App
8. Add a Widget extension
9. Inside widget: Add > Embed > Custom Element
10. Set source: Server URL > paste hosted bundle URL
11. Set tag name: `affective-ai-app`
12. Stretch Custom Element to fill widget (100% width/height)
13. Configure Installation Settings

**Phase 4 -- Deploy to Site**
14. Release a version of the Blocks app
15. Create/open Wix site for affective-ai.io
16. Install the Blocks app on the site
17. Set widget to full-page, remove Wix header/footer
18. Connect affective-ai.io domain in Wix dashboard
19. Publish

### Tradeoffs

**Pros:** Uses Wix Blocks as requested, domain managed by Wix, SSL included  
**Cons:** iframe sandboxing (~85% fidelity), hash URLs (`/#/technology`), no localStorage, SEO limitations, still needs external CDN for bundle, Wix wrapper performance overhead

---

## Option B: Wix Site with Full-Page HTML Embed

**Fidelity: ~90% | Complexity: MEDIUM | Maintenance: LOW**

Standard Wix site on affective-ai.io with a full-page HTML iframe embedding the React app hosted on Netlify/Vercel.

### Required Code Changes: None (app deploys as-is)

### Steps
1. `npm run build` the React app
2. Deploy `dist/` to Netlify
3. Create Wix site, connect affective-ai.io domain
4. Add full-page HTML embed iframe pointing to Netlify URL
5. Publish

**Pros:** Zero code changes, ~90% fidelity, simpler setup  
**Cons:** iframe wrapper, SEO limitations, slight load delay

---

## Option C: Direct Static Hosting (Best UX)

**Fidelity: 100% | Complexity: LOW | Maintenance: LOW**

Deploy the React SPA to Netlify/Vercel/Cloudflare Pages and point affective-ai.io DNS there directly.

### Required Code Changes: None

### Steps
1. `npm run build`
2. Deploy `dist/` to Netlify
3. Configure affective-ai.io DNS (CNAME to Netlify)
4. Auto-provisioned SSL
5. Done

**Pros:** 100% fidelity, best performance, full SEO, proper routing, free tier  
**Cons:** Domain not managed through Wix dashboard, Wix Blocks not used

---

## Recommendation

Since you explicitly requested Wix Blocks, **Option A** is the plan. However, be aware it requires:
- External hosting for the JS bundle regardless (Wix Blocks only hosts widget logic, not arbitrary static files)
- Code modifications to wrap the app as a Web Component
- Acceptance of ~85% visual fidelity due to iframe sandboxing

I recommend we proceed with Option A but keep Option C as a fallback if the Wix Blocks approach introduces unacceptable UX degradation.

---

## Prerequisites Before Starting

1. **Wix Account** with Wix Studio access (for Custom Apps)
2. **affective-ai.io domain** registered and DNS accessible
3. **Wix Premium Plan** (required for custom domain connection)
4. **Static hosting account** (Netlify free tier is sufficient for the bundle)
5. Login credentials for Wix when ready to proceed

---

## Estimated Timeline

| Phase | Duration | Depends On |
|---|---|---|
| Phase 1: Code prep | ~2 hours | None |
| Phase 2: Host bundle | ~30 min | Phase 1 |
| Phase 3: Wix Blocks setup | ~1 hour | Wix login credentials |
| Phase 4: Domain + publish | ~30 min | Phase 3 + DNS access |
| **Total** | **~4 hours** | |
