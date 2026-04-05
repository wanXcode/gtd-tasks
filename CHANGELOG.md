# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, adapted for this repo.

## [Unreleased]

### Added
- Added `scripts/gtd_reminder_digest.py` as the unified API-first reminder/query entry
- Added dual reminder modes: `morning` and `evening`
- Added JSON output support for manual “待办清单” queries and agent reuse
- Added `scripts/gtd_manual_query.sh` as a thin manual-query wrapper over the digest script

### Changed
- Switched formal reminder generation away from `today.md` / local cache inputs to direct API open-task reads
- Kept `render_views.py` in place as a display/cache rendering layer, not the reminder source
- Updated reminder prompts and AIGTD runtime docs to point manual list queries and scheduled reminders at the same digest chain
- Turned `daily-reminder.sh` into a compatibility wrapper around the new digest script

## [v0.2.2] - 2026-03-17

### Added
- Added `scripts/nlp_capture.py` for natural-language task capture with `preview` / `apply` modes
- Added rendered management views:
  - `done.md`
  - `weekly/review-latest.md`
- Added v0.2.2 release notes: `release-v0.2.2.md`

### Changed
- Expanded `scripts/render_views.py` to render `done.md` and weekly review output in addition to existing views
- Adjusted `scripts/task_cli.py` default add bucket from `today` to `future` to match v0.2.2 capture workflow
- Updated README to reflect v0.2.2 workflow, CLI coverage, and NLP capture usage
- Kept all business-time semantics aligned to `Asia/Shanghai`

### Fixed
- Fixed documentation mismatch between v0.2.2 requirements and actual CLI default capture behavior
- Fixed missing rendered artifacts for completion review and weekly review scenarios

## [v0.2.1] - 2026-03-17

### Added
- Added structured task datastore for main account: `data/tasks.json`
- Added data-layer docs: `data/README.md`
- Added main CLI tools:
  - `scripts/task_cli.py`
  - `scripts/render_views.py`
  - `scripts/migrate_legacy.py`
- Added wife data-layer initialization:
  - `users/wife/data/tasks.json`
  - `users/wife/data/README.md`
- Added wife helper scripts:
  - `users/wife/scripts/task_cli.py`
  - `users/wife/scripts/render_views.py`

### Changed
- Upgraded GTD repo from markdown-first management to JSON datastore + rendered views
- `today.md`, `inbox.md`, `matrix/*` now act as rendered views instead of source-of-truth files
- Unified business time semantics to `Asia/Shanghai`
- Updated root README to reflect v0.2.1 architecture
- Updated wife README to reflect structured data model
- Simplified rendered reminder text to remove hardcoded business-specific guidance
- Reworked migration script into a safe migration status checker

### Fixed
- Fixed mismatch between current GTD state and rendered markdown views
- Fixed scattered documentation around data ownership and migration expectations
- Fixed a rendering text encoding issue in Q4 output

## [v0.2.0] - 2026-03-10

### Added
- Introduced unified reminder template approach
- Added prompt/template consolidation under `prompts/`

### Changed
- Standardized GTD reminder template usage
- Clarified that template changes should be made in a single source

## [v0.1.0] - 2026-03-05

### Added
- Initial GTD task management repository
- Markdown-based workflow with `today.md`, `inbox.md`, `matrix/`, `archive/`, `weekly/`
- Deployment script and initial usage documentation
- OpenClaw cron-based reminder workflow
