# Verification checklist

Checked on 4 October 2026 against the assignment brief. Evidence comes from three places:

- **Automated tests:** 424 backend (pytest) and 97 frontend (Vitest), all passing; ruff, mypy
  strict, ESLint and the TypeScript check are clean.
- **Live scrapes** of the real sites (a full run, then an incremental re-run).
- **An end-to-end script** run against the production Docker image with the scraped data:
  **30/30 checks passed**.

Legend: ✅ verified · ⚠️ works with a known limit · ⬜ not done yet

## 1. Core requirements

| Requirement | Status | Evidence |
|---|---|---|
| Part-time / casual roles | ✅ | 148 open part-time listings |
| Full-time roles | ✅ | 454 open |
| Internships | ✅ | 9 open, plus internship wording in 16 titles |
| Everyday jobs (cafes, retail, delivery, tutoring) | ⚠️ | Retail 34, hospitality/bar/catering 43, delivery 7, teaching/tutoring 41. No cafe chain could be scraped legitimately (see 2.6) |
| Real listings from our own scraper, no job APIs | ✅ | requests + BeautifulSoup only; Greenhouse's JSON API deliberately not used |
| Listing view: title, employer, location, pay, job type, posted date | ✅ | All 6 shown on every card. Pay is shown as hourly where it can be computed (57%), otherwise as advertised, otherwise "Pay not stated" |
| Searchable and filterable | ✅ | Keyword, location, job type, pay, visa fit, trust, posted date, 3 sort orders, paging. Each one checked against live data |

## 2. Scraper (in depth)

### 2.1 It is our own code and handles real HTML

| Check | Status | Evidence |
|---|---|---|
| Fetching | ✅ | `PoliteSession`: browser-like user agent, 1.5–3.5 s random delay, robots.txt honoured (including Crawl-delay), retries with back-off on 429/5xx respecting `Retry-After`, charset detection |
| Parsing | ✅ | JSON-LD `JobPosting` first, then multi-candidate CSS selectors per field, so one site change does not break a field |
| Three different site types | ✅ | University board (Drupal table, pure CSS), student job board (paginated cards plus JSON-LD detail pages), employer ATS boards (Greenhouse HTML) |
| Offline parser tests on saved real pages | ✅ | `tests/fixtures/html/`, one per source and page type |

### 2.2 Depth added in this round

| Improvement | Why it matters | Evidence |
|---|---|---|
| **Listing lifecycle**: closed jobs leave search but stay for the tracker | Students should not apply to filled jobs | Closed on: detail page 404/410; StudentJob's own expired-jobs sitemap; a complete crawl of Cambridge or Greenhouse that no longer lists the job; or no sighting for 30 days. Reopened if seen again. 2 jobs closed in the live run |
| **Safety guards** on closing | A broken scraper must not empty the site | Never closes after a crawl with failed pages or limits; refuses to close more than 50% of a source at once (tested) |
| **Incremental re-scrapes** | Faster and kinder to the sites | Detail pages read in the last 3 days are not downloaded again. Re-run took **3.5 min instead of 20**, fetching 40 pages instead of ~470 |
| **Run history and health** | Problems are visible, not silent | Every run is recorded per source (`ok` / `partial` / `empty` / `failed`, counts, errors, field completeness). Shown at `/api/meta/sources`, by `cli status`, and on the jobs page ("611 open jobs from 3 sources · updated 3 minutes ago"; a failing source is named). An `empty` run (pages fetched but nothing parsed) flags a probable site redesign |
| **Deeper coverage** | More real choice | Cambridge now walks the whole search. StudentJob gains 11 everyday-job categories (hospitality, catering, cashier, shop assistant, delivery, warehouse, teaching, promotional). Greenhouse boards up to 5 pages. **60 → 611 open listings** |
| **Pay that reflects the job's real hours** | Weekly pay divided by a full-time week made part-time jobs look illegal | "£100–£400 per week" for 4–20 h/week = £20/h, not £2.67/h. Weekly pay without stated hours is only converted for full-time roles. StudentJob hourly pay: **10% → 56%** of listings |
| **Mislabelled salaries** | "£16,087 per month" became £100/h | Large weekly or monthly amounts are treated as annual; pro-rata salaries are not turned into misleading hourly rates. Every rate above £60/h is now a genuine senior salary |
| **Parser fixes reach old data** | No re-scrape needed after a fix | `rescore` re-derives hourly pay from the stored advert text, then trust and visa fit |

### 2.3 Live data after the full scrape and re-run (4 Oct 2026)

| Source | Pages | Listings | Pay (hourly) | Status |
|---|---:|---:|---:|---|
| University of Cambridge | 1 (all rows on one page) | 130 (143 rows, some duplicated) | 93% | ok |
| StudentJob UK | 276 | 285 | 56% | ok* |
| Greenhouse (Deliveroo, Monzo, GoCardless, IMC) | 199 | 196 | 34% | ok |

\*Reported as `partial` in that first run because category page limits were counted as
failures; fixed, and the re-run reports `ok`. Location, posted date and description: 100% for
every source. Failed pages: 0.

### 2.4 Politeness and safety

| Check | Status |
|---|---|
| robots.txt respected (StudentJob external-redirect links skipped, as disallowed) | ✅ |
| Delays between requests, back-off on 429/503 | ✅ |
| No proxy rotation or CAPTCHA solving | ✅ |
| Sites whose robots.txt blocks crawlers were not scraped (e.g. Caterer.com) | ✅ |
| Third-party front-end keys scrubbed from saved fixtures (GitHub secret-scanning alert) | ✅ |

### 2.5 Failure handling

| Scenario | Behaviour | Tested |
|---|---|---|
| One page fails to parse | Logged, skipped, run continues | ✅ |
| A whole source is down | Other sources still run; status `failed` | ✅ |
| Site redesign (selectors miss) | Status `empty`, CLI exits 1, warning on the jobs page | ✅ |
| Detail page now 404 | Listing closed, not counted as a failure | ✅ |
| Two scrapes at once | Second one refused | ✅ |

### 2.6 Known scraper limits

- **Cafe chains (Costa, Pret, Gail's and others)** use JavaScript-only applicant systems,
  block crawlers in robots.txt, or were unreachable. Cafe-type work is covered through
  hospitality and catering categories instead.
- **StudentJob is sampled**: the first 2 pages of each of 16 city and category listings, not
  all 5,900 jobs on the site. Its expired-jobs sitemap still retires anything we hold.
- **Visa fit is "unknown" for 76% of listings** because most adverts never mention visas. The UI
  says so plainly instead of guessing.

## 3. The three features

| Feature | Status | Evidence |
|---|---|---|
| **Trust score** (0–100 with reasons) | ✅ | Employer's own site vs third-party board, pay disclosed, scam phrases, income claims, ghost jobs (live over 45 days), pay below minimum or living wage. Reasons listed worst first |
| **Visa fit tags** (part of the trust feature) | ✅ | Student-friendly, sponsorship, right to work required, UK citizens only, and new: **self-employed** (freelance work is not allowed on a Student visa); 41 such listings found |
| **Application tracker with work-hour guard** | ✅ | Pipeline saved → applied → interviewing → offered/closed with invalid moves refused (409). Hours guard warns over 20 h/week (22 h tested), follow-up reminders after 7 quiet days, save/apply from the job page |
| **Private trackers** | ✅ | Each browser has an anonymous id; other visitors see and change nothing (tested) |
| **Resume match and enhancement** | ✅ | Fit score with matched and missing skills; edits highlighted in the resume (yellow = change, blue = new) to accept or reject; PDF/Word/text upload parsed in memory and never stored. Claude when a key is set, offline rules otherwise (tested with a real resume) |

## 4. Usability

| Check | Status | Evidence |
|---|---|---|
| Fast | ✅ | Search responds instantly on 611 listings; 3D scenes load lazily, never blocking the page |
| Phones | ✅ | Screenshots at 390 px: one-row filter bar, bottom-sheet menus, full-page job view |
| Accessibility | ✅ | Keyboard-reachable highlights and menus, focus kept inside the drawer, screen-reader labels; tests query by role and label |
| Empty, error and closed states | ✅ | Each has its own message; closed jobs show "no longer listed" and no Apply button |

## 5. Code quality and production readiness

| Check | Status |
|---|---|
| Layered backend (scraper / enrichment / repositories / services / API); all SQL in repositories | ✅ |
| Versioned database migrations (existing databases upgrade in place, tested) | ✅ |
| Production Docker image builds and runs; health check passes | ✅ |
| Same-origin static serving, security headers, per-visitor rate limit on resume tools | ✅ |
| Daily scrape inside the service (Render cron cannot reach the disk) | ✅ seen running in the container |
| Secrets: API key stored as a secret, never logged; `.env` not tracked | ✅ |

## 6. Deliverables

| Deliverable | Status |
|---|---|
| Working app (hosted link or run instructions) | ⬜ Ready to deploy to Render (`render.yaml`, `docs/DEPLOY.md`); not yet deployed |
| Source code (repo link) | ✅ GitHub (local commits waiting to be pushed) |
| 1-page write-up (scraper + rationale for 3 features) | ⬜ To do |
| Video walkthrough in the README | ⬜ README to do; video to record |
