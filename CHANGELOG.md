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
- Added Python and JavaScript regression tests for the full node pack.
- Added the `MengBaoEcommerceSettings` node with product information, layout,
  typography, reverse-page, and model controls based on the MengBaoAI one-click
  e-commerce workflow.
- Added `MengBaoSmartCollage` with gapless, aspect-preserving layout and parallel
  add/remove image buttons, retaining four sockets by default and supporting up to twenty.
- Added `MengBaoImageConstraint` for aspect-preserving size limits and optional
  center cropping when minimum and maximum constraints conflict.
- Added `MengBaoGlobalAPIKey` with a password input and explicit save/clear buttons,
  shared user-directory storage, safe status output, and automatic balance updates.
- Added safe key clearing that preserves unrelated settings and prevents legacy
  key migration from restoring a deliberately cleared key.
- Added shared floating launchers for the prompt library, material library and generation history.
- Added searchable local materials, image output placeholders, and material/prompt library actions beneath saved and previewed images.
- Added persistent generation history with progress, status, image previews and filters.
- Added image reverse analysis, visual replica settings and optional replica audits, with cached GEM 3.7/3.8 primary/fallback requests.
- Added automatic editor closing only after replica settings are successfully confirmed.
- Added bilingual Registry metadata, runtime-only archive filtering, Windows/Linux CI and extracted archive validation for all 17 nodes.
- Added explicit Registry token preflight; a missing publishing token no longer appears as a successful release.

### Changed

- Changed the immutable Comfy Registry package ID to `mengbaoai` for the new unified package.
- Moved runtime code into `nodes/`, `api/`, `utils/`, and `web/js/` modules.
- Standardized categories under `萌宝AI/图像API`, `萌宝AI/图像处理`, `萌宝AI/提示词`, `萌宝AI/电商`, and `萌宝AI/基础`.

### Compatibility

- Preserved the historical Image API, split/crop/picker and prompt node IDs while adding new nodes.
- Replaced the old `WANGLoadImageUploadPaste` registration with `MengBaoLoadImage`; workflows using that legacy loader require replacing it and reconnecting its ports.
- Preserved `/wang_prompt_organizer/*` HTTP routes for existing frontend integrations.
- Kept the old `mengbao-image-api` Registry package as a separate Legacy upgrade path.
