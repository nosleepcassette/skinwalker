# Skinwalker Roadmap

## Scope Decisions

- Keep the existing bundled palette catalog. Do not spend roadmap time on adding new built-in color schemes.
- Focus color work on organization, browsing, readability checks, per-field overrides, and reset/import flows.
- Treat advanced image-to-ASCII work as a shared engine for Skinwalker first, with standalone extraction optional later.
- Treat AI generation as opt-in assistive tooling, not the primary editing path.

## Phase 1: Foundation

- Add a real test suite for model normalization, Hermes bridge behavior, generator helpers, and app state transitions
- Fix library edge cases such as duplicate visible skin names from multiple YAML files
- Separate persisted draft state from transient generator state
- Add whole-skin YAML import/export with validation and collision handling
- Add explicit profile targeting for activation and profile-aware config writes
- Add a draft diagnostics surface for validation, save errors, and import failures

## Phase 2: Workflow And UX

- Add app-level undo/redo across all edits, not just widget-local text changes
- Add better keyboard navigation across the tall form
- Add per-field select-all, clear, and reset affordances for large text inputs
- Add section-level actions for spinner, logo, hero, and palette tools
- Add modified-field and modified-section highlighting
- Add an active-vs-draft diff view
- Add autosave and crash-recovery snapshots for the current draft

## Phase 3: Color UX

- Add a palette browser with live swatches and preview-before-apply
- Add categorization and tags for the existing palette set
- Add a per-field color picker instead of raw token editing only
- Add contrast warnings for weak prompt, banner, and response combinations
- Add reset-to-preset behavior and "modified from preset" indicators
- Add better palette import/export flows for pasted or file-based schemes

## Phase 4: Font System

- Replace the flat searchable font list with categorized browsing
- Add live preview for the highlighted font
- Add preview-all mode for the filtered result set
- Add favorites, recents, and featured fonts
- Add clearer distinction between logo generator controls and persisted banner markup

## Phase 5: Hero / Image Lab

- Build a richer image-to-ASCII engine with gradients, filters, and dithering
- Add source-image preview, crop/fit controls, and width-aware output preview
- Support threshold, sharpen, edge detection, invert, contrast, and padding controls
- Add direct apply-to-hero and export-to-text/image flows

## Phase 6: AI-Assisted Generation

- Add Hermes-first generation for branding bundles, spinner bundles, and art prompts
- Support environment-key fallbacks when Hermes is unavailable
- Require structured outputs and explicit user acceptance before applying changes
- Add assisted palette tuning rather than new bundled palette creation

## Later

- Optional `/skin edit` launcher inside Hermes itself
- Optional standalone text/image tools once the shared engines stabilize
- Better support for future Hermes theme extensions such as light/dark mode variants
