# Affective AI — Option B Deployment Plan
## Full-Page HTML Embed on Wix + GitHub Pages Static Hosting

**Date:** 2026-03-11  
**Artifact:** `apps/web/dev/` (React 18 + Vite 5 + Tailwind CSS 3)  
**Target domain:** https://affective-ai.io  
**Approach:** Deploy built SPA to GitHub Pages, embed full-page in Wix site  
**Estimated fidelity:** ~90%

---

## Architecture

```
User visits affective-ai.io
        |
        v
  Wix Site (manages domain, SSL)
        |
        v
  Full-page iframe / HTML embed
        |
        v
  GitHub Pages React SPA (all animations, routing, interactivity)
  https://rustybee2016.github.io/project-reachy-emotion/
```

---

## Code Changes Made

| File | Change | Why |
|---|---|---|
| `vite.config.js` | Added `base: '/project-reachy-emotion/'` | GitHub Pages serves from repo subpath |
| `src/App.jsx` | `BrowserRouter` → `HashRouter` | Works inside iframe + GitHub Pages |
| `package.json` | Added `homepage`, `predeploy`, `deploy` scripts | `gh-pages` CLI deployment |
| `public/404.html` | SPA redirect for GitHub Pages | Handles direct URL access |
| `public/_redirects` | Netlify-style (harmless, ignored by GH Pages) | No-op fallback |

---

## Fidelity Analysis (~90%)

| Concern | Impact | Mitigation |
|---|---|---|
| iframe wrapper adds slight load delay | LOW | GitHub CDN is fast; perceived delay < 200ms |
| Wix header/footer may show briefly | MEDIUM | Use blank Wix template; hide header/footer |
| Address bar shows affective-ai.io (no inner route) | LOW | Acceptable for marketing site |
| SEO: crawlers see Wix page, not React content | MEDIUM | Add meta tags + description to Wix page |
| Mobile: iframe scrolling | LOW | Set iframe to 100vw/100vh with overflow handling |
| Hash-based URLs (`/#/technology`) | LOW | Invisible to users in iframe context |

---

## Phase 1: Build & Deploy to GitHub Pages

### Completed Steps

- [x] **Step 1:** Configured `vite.config.js` with `base: '/project-reachy-emotion/'`
- [x] **Step 2:** Switched `BrowserRouter` → `HashRouter` in `App.jsx`
- [x] **Step 3:** Added `homepage` and deploy scripts to `package.json`
- [x] **Step 4:** Created `public/404.html` for SPA routing
- [x] **Step 5:** Installed `gh-pages` package
- [x] **Step 6:** Ran `npm run deploy` — published to `gh-pages` branch
- [x] **Step 7:** Verified `gh-pages` branch exists on `origin`

### Remaining Step (Requires Repo Admin)

- [ ] **Step 8:** Enable GitHub Pages in repo settings (see instructions below)

#### How to Enable GitHub Pages

1. Go to: https://github.com/RustyBee2016/project-reachy-emotion/settings/pages
2. Under **Source**, select: **Deploy from a branch**
3. Under **Branch**, select: `gh-pages` / `/ (root)`
4. Click **Save**
5. Wait 1-2 minutes for deployment
6. Verify at: https://rustybee2016.github.io/project-reachy-emotion/

---

## Phase 2: Wix Site Configuration (Wix Login Required)

- [ ] **Step 9:** Log into Wix dashboard
- [ ] **Step 10:** Create a new blank site (or open existing site for affective-ai.io)
- [ ] **Step 11:** Remove/hide default Wix header, footer, and navigation
- [ ] **Step 12:** Add a full-page HTML embed element (see embed code below)
- [ ] **Step 13:** Connect affective-ai.io domain in Wix Domains settings
- [ ] **Step 14:** Publish the Wix site
- [ ] **Step 15:** Verify at https://affective-ai.io

### Wix Embed Code (for Step 12)

In the Wix Editor:
1. Click **Add (+)** → **Embed Code** → **Custom Element** or **HTML iframe**
2. Choose **"Enter Code"** and paste:

```html
<style>
  html, body {
    margin: 0;
    padding: 0;
    overflow: hidden;
    height: 100%;
    background: #080818;
  }
</style>
<iframe
  src="https://rustybee2016.github.io/project-reachy-emotion/"
  style="position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; border: none; z-index: 9999;"
  allow="autoplay; fullscreen"
  loading="eager"
  title="Affective AI — Emotionally Intelligent Robotics"
></iframe>
```

3. Resize the HTML element to fill the entire page
4. Set the page background to `#080818` to match during load

### Wix Page Settings

- **Page title:** Affective AI — Emotionally Intelligent Robotics
- **Meta description:** Privacy-first emotion recognition meets empathetic robotics. Real-time EQ-driven human-robot interaction, on-premise, auditable, and trustworthy.
- **Hide header:** Yes
- **Hide footer:** Yes
- **Page margins:** 0

---

## Redeployment

To update the site after code changes:

```bash
cd apps/web/dev
npm run deploy
```

This rebuilds and pushes to the `gh-pages` branch. GitHub Pages auto-updates within ~1 minute.

---

## Status

| Phase | Status | Blocker |
|---|---|---|
| Phase 1 (Build + GitHub Pages) | **ALMOST DONE** | Enable GitHub Pages in repo settings |
| Phase 2 (Wix site setup) | BLOCKED | Wix login credentials needed |
