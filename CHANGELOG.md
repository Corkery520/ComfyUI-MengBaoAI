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
- Added `MengBaoSmartCollage` with the reference one-to-four image layout rules.
- Added `MengBaoImageConstraint` for aspect-preserving size limits and optional
  center cropping when minimum and maximum constraints conflict.

### Changed

- Changed the immutable Comfy Registry package ID to `mengbaoai` for the new unified package.
- Moved runtime code into `nodes/`, `api/`, `utils/`, and `web/js/` modules.
- Standardized categories under `萌宝AI/图像API`, `萌宝AI/图像处理`, and `萌宝AI/提示词`.

### Compatibility

- Preserved all seven historical ComfyUI node IDs while adding new e-commerce and image utility nodes.
- Preserved `/wang_prompt_organizer/*` HTTP routes for existing frontend integrations.
- Kept the old `mengbao-image-api` Registry package as a separate Legacy upgrade path.
