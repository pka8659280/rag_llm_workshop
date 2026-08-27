# Plan: Redesign the Two Web Pages with Bootstrap 5 (Less Custom CSS)

## Summary

Rebuild [static/chat.html](file:///c:/Users/User/VisualStudioCodeWorkspace/rag_llm_workshop/static/chat.html) and [static/reviews.html](file:///c:/Users/User/VisualStudioCodeWorkspace/rag_llm_workshop/static/reviews.html) using **Bootstrap 5 from the jsdelivr CDN**, replacing the current hand-written CSS with Bootstrap components/utilities and keeping only a tiny custom `<style>` block (~10 lines) for things Bootstrap cannot express (message-bubble wrapping, star colors). All existing functionality and JavaScript IDs are preserved, so the FastAPI backend ([web_app.py](file:///c:/Users/User/VisualStudioCodeWorkspace/rag_llm_workshop/web_app.py)) needs **no changes**.

## Current State Analysis

- `web_app.py` serves the two static HTML pages at `/` and `/reviews` and exposes `/api/chat`, `/api/reviews`, `/api/search`; static assets are mounted at `/static` (no backend change required).
- `static/chat.html` — ~165 lines, custom CSS: gradient body background, `.info-card`, `.chat-container`, `.message.bot/.user`, `.error-banner`, FAB (`.fab` + `.fab-menu`). JS: `addMessage`, `showError`, `sendMessage`; elements `chatMessages`, `userInput`, `sendBtn`, `errorBanner`, `fabBtn`, `fabMenu`.
- `static/reviews.html` — ~300 lines, custom CSS: `.card`, `.stats-bar`, `.filters`, table styling, `.pagination`, `.search-box`, `.result-card`, `.empty-msg`, FAB. JS: `starsHtml`, `esc`, `buildQuery`, `loadReviews`, `changePage`, `applyFilters`, `resetFilters`, `runSearch`, `init`; elements `totalLabel`, `filterStar`, `filterDish`, `filterOrder`, `filterQ`, `tableBody`, `pageInfo`, `prevBtn`, `nextBtn`, `searchQuery`, `searchK`, `searchResults`, `fabBtn`, `fabMenu`.
- Decisions (user-confirmed): **Bootstrap via CDN**, **default Bootstrap look** (Bootstrap primary blue, no gradient branding).

## Proposed Changes

### 1. Rebuild `static/chat.html` with Bootstrap 5

- **Head**: link Bootstrap 5 CSS from jsdelivr; include the tiny custom `<style>` block.
- **Navbar** (`navbar navbar-expand navbar-dark bg-primary`): brand "🍽️ ABC123 Restaurant" + nav links `💬 Chat` (`/`, `.active`) and `🗄️ Review DB` (`/reviews`).
- **Body background**: `bg-light` (Bootstrap utility) instead of the gradient.
- **"About This Chat"** → Bootstrap `card` + `list-group list-group-flush`.
- **Chat panel** → `card`:
  - header: `card-header bg-primary text-white`
  - messages: `card-body` with `overflow-auto`, fixed height via inline `style="height: 380px"` (one utility line, or a `.chat-messages` class in the custom block)
  - bubbles: `d-flex flex-column`, bot = `align-self-start bg-light rounded p-2 mb-2` + `.message` custom class (for `white-space: pre-wrap` and `max-width: 80%`), user = `align-self-end bg-primary text-white rounded p-2 mb-2`
  - input: `input-group` with `form-control` + `btn btn-primary` (id `sendBtn`)
- **Error banner**: Bootstrap `alert alert-danger` with `d-none` initially; `showError()` removes `d-none`, hides with `d-none`.
- **FAB**: keep it, but express with Bootstrap utilities + dropdown component — button `position-fixed bottom-0 end-0 m-4 rounded-circle btn btn-primary shadow` (id `fabBtn`), menu as Bootstrap `dropdown-menu` inside a `dropup` container aligned `dropdown-menu-end`; Bootstrap's bundle JS handles open/close and click-outside (replace the manual `toggleFab` click-outside logic with Bootstrap's dropdown). Menu items: `dropdown-item` links to `/` and `/reviews`, current page as `dropdown-item active`.
- **JS**: keep `addMessage` / `showError` / `sendMessage` logic unchanged (same element IDs). Remove the custom `toggleFab`/click-outside code; the dropdown component replaces it (FAB toggles via `data-bs-toggle="dropdown"`).
- Include Bootstrap bundle JS at end of `<body>`.

### 2. Rebuild `static/reviews.html` with Bootstrap 5

- **Head**: same Bootstrap CSS + tiny custom `<style>` block (star colors, `.text-cell` wrapping).
- **Navbar**: same as chat page with `🗄️ Review DB` as `.active`.
- **Stats + filters** → `card` with `card-body`:
  - stats: `<h5 id="totalLabel">` + `badge bg-primary`
  - filters: `<form>` using `form-label`/`form-select`/`form-control` in a `row g-2` grid; Apply = `btn btn-primary`, Reset = `btn btn-outline-secondary`
- **Table** → `card` + `table table-striped table-hover align-middle`, `.text-cell` custom class keeps `white-space: pre-wrap; max-width: 380px`.
- **Pagination**: Bootstrap `pagination pagination-sm justify-content-between` with `page-link` buttons (ids `prevBtn`/`nextBtn` kept) + `page-info` span.
- **Semantic search** → `card`: `input-group` with `form-control` (id `searchQuery`) + `form-select` (id `searchK`) + `btn btn-primary` (Search); results rendered as `list-group` items (`.result-card` replaced by `list-group-item`, score as `badge bg-primary rounded-pill`).
- **FAB**: identical dropup dropdown as chat page.
- **JS**: keep all functions/element IDs unchanged; only adjust the result-card HTML produced by `runSearch()` to use Bootstrap classes (`list-group-item`, `badge`).

### 3. Shared minimal custom CSS (in both pages)

Small `<style>` block containing only: `.message { max-width: 80%; white-space: pre-wrap; word-wrap: break-word; }`, `.stars .empty { color: #d9d9d9; }`, `.text-cell { max-width: 380px; white-space: pre-wrap; word-wrap: break-word; }`. Everything else uses Bootstrap utilities/components.

### 4. Minor doc note in `Step_5_web_ui_run_guideline.md`

Add one line under Notes: "The two pages load Bootstrap 5 from the jsdelivr CDN, so the browser needs internet access to display the styled layout." (No other doc changes.)

## Assumptions & Decisions

- **Bootstrap 5.3 CDN** (`https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/...` CSS + bundle JS), default primary color.
- The **FAB stays** (it was requested previously) but is reimplemented with Bootstrap utilities + the dropdown component → effectively zero custom CSS.
- **Backend untouched**: pages keep all current element IDs and fetch calls; `web_app.py` and API endpoints unchanged.
- No npm/pip installs, no build step.

## Verification

1. Server already running (`uvicorn web_app:app --port 8000`); both pages must return HTTP 200.
2. `curl` both pages and confirm they contain `cdn.jsdelivr.net` Bootstrap links and the Bootstrap bundle script.
3. Chat page: send an on-topic question via `/api/chat` → real RAG answer; off-topic → refusal (API unaffected, sanity check).
4. Reviews page: `/api/reviews?star_rating=5&limit=5` still returns data with metadata (backend untouched).
5. Visual check in browser: pages render with Bootstrap navbar/cards, table styled, FAB dropdown opens upward and navigates to both pages, chat bubbles left/right aligned.
6. Check browser console for JS errors after the redesign (the only JS change is the FAB: from custom toggle to Bootstrap dropdown).
