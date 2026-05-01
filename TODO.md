# Whipple Report AI - TODO

> Claude-managed. Edit via Claude session or Git. Never delete items - move to Done.

## Ready to Build

- [ ] **Wire scraper selectors for high-value whipple-archive sources** - Reuters/Bloomberg/WSJ/SP-Global/Rigzone all bootstrapped as `source_type=scraper` but have no `selector_config`. They fail every tick if enabled. Each needs custom CSS selectors (item_selector + link_selector + title_selector) against their HTML. Highest value: Reuters (99 cites), Bloomberg (67), WSJ (39), S&P Global (26). OilPrice already covered via modern RSS. Defer until after first successful weekend run validates the rest of the pipeline.

## Backlog

- [ ] **Manual source curation pass after first 1-2 weekend runs** - Review which active sources actually contributed to bulletins, deweight or disable noisy ones, raise weights on high-quality contributors.
- [ ] **Add Cortex MCP tools for tick/finalize triggers + status** - Currently Whipple posts to Cortex /api/notify directly via requests; no Cortex MCP integration. Could expose tick/finalize triggers + pipeline status as Cortex tools for Sentinel-driven control.

## Bugs

- [ ] **datetime.utcnow() deprecation warnings** - 117 warnings on every test run, all from `datetime.utcnow()` usage in models.py and pipeline modules. Python 3.12+ wants timezone-aware `datetime.now(datetime.UTC)`. Functional but noisy in pytest output.

## Someday/Maybe

- [ ] **Pre-2020 archive mining via Wayback Machine** - resilience.org's sitemap only goes back to 2020-03. Earlier Tom Whipple work lived on energybulletin.net before the 2014 merger. Wayback Machine has snapshots; could extract source citations from older bulletins for richer source set. Probably not worth the effort unless source coverage feels thin.
- [ ] **Per-source RSS feed health page** - /sources already shows `last_success` and `consecutive_failures`, but a dedicated health page with item-arrival timeline per source would help diagnose stale/dead feeds.
- [ ] **Section-level regenerate UI** - If a bulletin has a bad section, allow regenerating just that section without re-running the whole compose stage. Requires partial-regenerate support in `compose()`.
- [ ] **Public archive viewer at whipple.lfconnect.vip** - Currently /archives is LAN-only at 192.168.86.204:28813. Could expose via NPM if Dillon ever wants to share past bulletins externally.

## Done

### v0.1 - Initial Build (2026-05-01)

- [x] **Phase 0 - Scaffold + deploy** - Project structure, SQLAlchemy schema (Source/Article/Bulletin/GeminiCall/Run with state machine), Flask factory + /health, Dockerfile + compose on subnet 172.64.0.0/24, backup-agent DockerVolumeJob registration (90d retention, nightly NAS), Uptime Kuma monitor #89, home-hub Tools tile - 2026-05-01
- [x] **Phase 1 - Pipeline stages** - Gemini service (rate limiter at 14 RPM/1450 RPD + retry + call logging), voice guide + classify/summarize/compose prompts, scrape stage (RSS + HTML scraper), classify (Flash), select (recency + source weight + diversity penalty), summarize (Pro for narrative, Flash for briefs), compose + Jinja bulletin renderer, Gmail send service via OAuth refresh token, tick + finalize orchestrators with Run logging + Cortex /api/notify - 2026-05-01
- [x] **Phase 2 - Web UI + tests** - Archive miner (sitemap-based with WHIPPLE_PRE_DECLINE_CUTOFF=2022-09-30), bootstrap, /sources management UI, /archives + /archives/<week_of> + /manual (phrase-gated tick/finalize/skip-week/resend) + /rss routes, Playwright e2e smoke (5 tests). 30 unit + e2e total green - 2026-05-01
- [x] **T19 - Production setup** - Bootstrap mined 30 evenly-sampled pre-cutoff bulletins from 2020-2022 (vs initial 6 from Sep-Oct 2022 single-page-scrape bug), 22 whipple-archive sources discovered. Gmail OAuth wired via separate "Whipple Report" Cloud project (published-not-test for permanent refresh token), OAuth flow ran from PC-KL because container is headless, test email sent (msg id 19de570f1da7f8c9). Weekend cron installed: Sat 6-23h hourly tick + Sun 0-20h hourly tick + Sun 21h finalize - 2026-05-01
- [x] **/sources UI redesign** - B-Material slide toggles, master toggle in header row, 7 bulk actions (enable_all, disable_all, enable_modern, enable_whipple_rss [excludes defunct], disable_whipple, disable_noise [bsky/fb/x/linkedin share buttons], disable_defunct [energybulletin.org/daily.energybulletin.org]) - 2026-05-01
