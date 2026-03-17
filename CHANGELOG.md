# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, adapted for this repo.

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
