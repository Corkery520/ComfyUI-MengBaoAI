# Changelog

All notable changes to this project are documented in this file.

## [1.1.0] - 2026-09-16

### Changed

- Upgraded the repository to a unified MengBao AI node pack architecture.
- Added centralized node registration under `nodes/` with duplicate ID checks.
- Moved the existing node to the `萌宝AI/图像生成` category and unified its display name.
- Preserved the historical `WANGImageAPI` ID for existing workflow compatibility.
- Added `docs/NODE_DEVELOPMENT.md` for future nodes and category conventions.

## [1.0.0] - 2026-09-16

### Added

- Initial ComfyUI Registry release under the package ID `mengbao-image-api`.
- Text-to-image, image-to-image, and multi-image reference workflows.
- GPT Image 2/2.5 and Nano Banana 2/Pro model mappings.
- Transparent background controls, balance query controls, and localized Chinese/English UI.
- ComfyUI Registry metadata and automated GitHub Actions publishing.
