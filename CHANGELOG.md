# Changelog

All notable changes to this project are documented in this file.

## [1.0.0] - 2026-09-16

### Added

- Established `ComfyUI-MengBaoAI` as the unified MengBaoAI ComfyUI node pack.
- Integrated Image API, image split/crop, image loading, prompt organizer, and prompt reader nodes.
- Added centralized node registration with duplicate ID, display name, and category validation.
- Added Chinese and English node localization with live `Comfy.Locale` updates.
- Added file selection and `Ctrl+V` support for image loading, preview images, and prompt JSON imports.
- Added user-directory storage and one-time migration for saved API keys and prompt data.
- Added Python and JavaScript regression tests for all seven nodes.

### Changed

- Changed the immutable Comfy Registry package ID to `mengbaoai` for the new unified package.
- Moved runtime code into `nodes/`, `api/`, `utils/`, and `web/js/` modules.
- Standardized categories under `萌宝AI/图像API`, `萌宝AI/图像处理`, and `萌宝AI/提示词`.

### Compatibility

- Preserved all seven historical ComfyUI node IDs.
- Preserved `/wang_prompt_organizer/*` HTTP routes for existing frontend integrations.
- Kept the old `mengbao-image-api` Registry package as a separate Legacy upgrade path.
