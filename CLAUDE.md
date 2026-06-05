# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository actually is

This repo (`open-star-tennis`) is **the deployed production build of a single-page app, not its source.**
It contains only compiled, minified output:

- `index.html` — the SPA entry point
- `assets/*.js`, `assets/*.css` — Vite-bundled, content-hashed chunks

There is **no source tree, no `package.json`, no Vite config, and no test/lint tooling** in this repo. The
`main` and `gh-pages` branches both hold the same build artifact; `gh-pages` is the repository's default
(HEAD) branch and serves the live GitHub Pages site at base path `/open-star-tennis/`.

Implications you must keep in mind:

- You **cannot** `npm install`, `npm run build`, or run tests here — none of that tooling exists in the repo.
- The Vue/Vite **source lives in a separate, upstream repository that is not checked in here.** Real feature
  work happens there, then a fresh build is copied into this repo to publish. Editing the minified bundles in
  `assets/` by hand is the only change possible from within this repo and should be avoided except for trivial,
  unavoidable patches.
- All asset filenames are content-hashed (e.g. `index-DKkqJ8T_.js`). They change on every rebuild, and
  `index.html` references them by exact name, so the HTML and the `assets/` directory must always be replaced
  together as a matched set.

## The application

"OPeN STAR 网球教务系统" — a Chinese-language management system for a tennis academy (student records, sales
leads, and court scheduling). The UI is in Simplified Chinese.

### Stack (inferred from the bundles)

- **Vue 3** (3.5.x) + **Vue Router**, built with **Vite**.
- **Vue Router in HTML5 history mode**, base `/open-star-tennis/`. Note there is **no `404.html` fallback** on
  the gh-pages deployment, so deep-linking or refreshing on a route other than the root may 404 on GitHub Pages.
- **Supabase** as the entire backend (auth + database). There is no custom API server.

### Backend / Supabase

- Project URL `https://zdyjyqavtfxrtreyzgoe.supabase.co` and the **publishable (anon) key** are embedded in the
  JS bundle. This is normal for Supabase anon keys — they are designed to be public, so **data access must be
  protected by Row Level Security policies on the Supabase side**, not by hiding the key.
- Auth is Supabase Auth (gotrue): `signInWithPassword`, `getSession`, `getUser`, `onAuthStateChange`, `signOut`.
  JWT verification runs in-browser via WebCrypto.

### Routing & auth flow

- `/` → **Login** (public, `requiresAuth: false`)
- `/dashboard` → **Dashboard** (运营概览, operations overview)
- `/profiles` → **Profiles** (学员档案, student records)
- `/schedules` → **Schedules** (场地排课, court scheduling — minimal/stub chunk)
- `/leads` → **Leads** (线索, sales-lead pipeline)

Authenticated routes are gated by a global `router.beforeEach` guard that redirects unauthenticated users to the
login page. Each page is a **lazy-loaded chunk** (`Login`, `Dashboard`, `Profiles`, `Schedules`, `Leads`),
split out from the main `index` bundle; `vendor` holds the framework dependencies.

### Data model (Supabase tables used by the app)

- **`profiles`** — students. Used by Profiles (CRUD) and Dashboard. Fields seen include name (姓名),
  phone (手机号, used as a lookup key), age (年龄), level (等级), source (来源), notes (备注), created time.
- **`leads`** — sales leads. Used by Leads (CRUD) and Dashboard. Modeled as a pipeline with a `status`
  (新客户 new → 已试听 trialed → 已报课 enrolled / 失败 lost) and a lead source (转介绍 referral, 美团 Meituan,
  朋友圈 WeChat moments, 线下活动 offline event, 其他 other).

## Working in this repo

Because there is no build system here, the only meaningful local task is serving the static files to preview the
deployed site. Serve from the repo root and open the `/open-star-tennis/` base path, e.g.:

```sh
python3 -m http.server 8000   # then visit http://localhost:8000/  (note: app expects base /open-star-tennis/)
```

The app will attempt to reach the live Supabase backend, so login and data require valid Supabase credentials.

### Deployment

This repo *is* the published artifact. The live site is GitHub Pages served from the `gh-pages` branch. To
publish an updated build, replace `index.html` and the entire `assets/` directory with freshly generated output
from the upstream source project (matched set — see above), commit, and push to `gh-pages`. Per this session's
branch policy, develop on the assigned feature branch and push there; do not push directly to `gh-pages` without
explicit permission.
