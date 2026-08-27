# Plan: Verify & Finish the Bootstrap Redesign

## Summary

The Bootstrap 5 redesign of the two web pages ([static/chat.html](file:///c:/Users/User/VisualStudioCodeWorkspace/rag_llm_workshop/static/chat.html) and [static/reviews.html](file:///c:/Users/User/VisualStudioCodeWorkspace/rag_llm_workshop/static/reviews.html)) is **already implemented and live**. This plan covers the remaining verification of that implementation per the approved [bootstrap_redesign_plan.md](file:///c:/Users/User/VisualStudioCodeWorkspace/rag_llm_workshop/.trae/documents/bootstrap_redesign_plan.md): confirm the pages render correctly in a browser, the FAB dropdown works, the chat API still answers, and there are no console errors — fixing anything found.

## Current State Analysis

- Both pages now load **Bootstrap 5.3.3 from the jsdelivr CDN** (CSS + bundle JS) and use only a tiny custom `<style>` block (`.message`, `.stars`, `.text-cell`).
- chat.html: `navbar bg-primary` with Chat/Review DB links, About `card` + `list-group`, chat `card` with `d-flex` bubbles, `input-group` send box, `alert-danger` error banner, FAB as `dropup dropdown-menu-end` (pure Bootstrap).
- reviews.html: same navbar, stats `h5` + `badge`, filter `<form>` with `form-select`/`form-control`, `table table-striped table-hover`, pagination buttons, semantic-search `input-group` rendering `list-group` results, FAB dropup dropdown.
- Backend [web_app.py](file:///c:/Users/User/VisualStudioCodeWorkspace/rag_llm_workshop/web_app.py) unchanged; API endpoints `/api/chat`, `/api/reviews`, `/api/search` untouched.
- [Step_5_web_ui_run_guideline.md](file:///c:/Users/User/VisualStudioCodeWorkspace/rag_llm_workshop/Step_5_web_ui_run_guideline.md) already has the CDN note.
- Already verified via curl: `/` and `/reviews` return HTTP 200; both contain `cdn.jsdelivr.net/npm/bootstrap@5.3.3` links; `/api/reviews?star_rating=5&limit=2` returns data with metadata.

## Proposed Changes (Verification Only)

No code changes are planned; this is a verify-and-fix cycle. The remaining checks from the original plan:

### 1. API sanity (curl)
- `POST /api/chat` with an on-topic question → expect a real RAG answer (JSON `{"answer": ...}`).
- `POST /api/chat` with an off-topic question → expect the refusal message.
- `POST /api/search` with e.g. `{"query":"kolo mee","k":3}` → expect results with scores.
- `GET /api/reviews?star_rating=5&limit=5` → expect 20 total (sanity, already passed once).

### 2. Visual browser check (browser_use subagent)
- Open `http://localhost:8000/`:
  - navbar renders with brand + active "Chat" link; About card and chat card visible
  - send a question → user bubble right (primary), bot bubble left (light), no layout breakage
  - FAB (bottom-right circle) opens a menu that navigates to `/reviews`
- Open `http://localhost:8000/reviews`:
  - table renders with rows + stars; filters Apply/Reset work; pagination updates
  - semantic search returns list-group results with score badges
  - FAB navigates back to `/`
- Capture **browser console messages** on both pages — no JS errors expected (the only JS change was the FAB: from custom toggle to Bootstrap dropdown).

### 3. Fix anything found
- If the browser check or console reveals issues (e.g., dropdown not opening, bubbles misaligned, search results unstyled), fix them in the relevant page with Bootstrap-consistent markup.
- Re-run the affected checks after any fix.

## Assumptions & Decisions

- The server is already running (`uvicorn web_app:app --port 8000`); reuse it. If it is not running, start it first.
- The browser must have internet access to load Bootstrap from the CDN (already documented in Step_5).
- No backend changes, no new files, no new dependencies.

## Verification

1. All API sanity checks above return the expected JSON.
2. Browser check of both pages passes with zero console errors.
3. FAB dropdown opens upward, highlights the current page, and navigates between `/` and `/reviews`.
4. Report the outcome; if all checks pass, the Bootstrap redesign is considered complete.
