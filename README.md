# Skinwalker

Skinwalker is a Textual-based TUI for creating, editing, previewing, and activating Hermes CLI skins.

It is aimed at the full Hermes skin surface rather than a toy theme picker. The app reads real built-in skins from Hermes, edits the real skin schema, saves custom skins into the active Hermes home, and previews the result as terminal-native output plus generated YAML.

## What It Does Today

The current app supports:

- browsing built-in and custom Hermes skins
- editing the real Hermes skin schema
- saving custom skins into `~/.hermes/skins/`
- activating a skin by updating `display.skin` in the active Hermes `config.yaml`
- terminal-native live preview
- generated YAML preview
- logo generation from text via `pyfiglet`
- first-pass hero generation from an image path via Pillow
- palette presets with live swatch preview
- direct color editing with target selectors and adjustment actions
- palette import from pasted text or a file path
- spinner preset shelf with waiting/thinking/wings bundles
- logo and hero generation controls for justification and flexible vs fixed-width output
- logo and hero art import from text or a file path
- searchable font browser for logo generation
- emoji and symbol picker for spinner, prompt, tool, and art text fields
- focused-field clear/reset helpers
- tabbed editor panes for identity, colors, spinner, and art
- `Save As` for built-in or otherwise non-directly-saveable drafts
- unsaved-change confirmation before replacing the current draft

## Project Status

This repository is in the "strong MVP" stage.

The app already works as a real Hermes skin editor, but it still needs a substantial UX and architecture pass in a few areas:

- app-level undo/redo
- better large-text editing ergonomics
- profile-aware targeting in the UI
- stronger library handling around duplicate names and imports
- richer font organization and live previews
- a much more capable hero/image-to-ASCII pipeline
- test coverage

Those upgrades are now spec'd in:

- [ROADMAP.md](/Users/maps/dev/skinwalker/ROADMAP.md)
- [SKINWALKER_UPGRADE_PLAN.md](/Users/maps/dev/skinwalker/SKINWALKER_UPGRADE_PLAN.md)

## Requirements

- Python 3.13+
- a local Hermes checkout at `~/.hermes/hermes-agent`

You can override the Hermes source root with:

- `--hermes-root`
- `HERMES_AGENT_ROOT`

Skin data is resolved relative to the active Hermes home. In default Hermes usage this means:

- skins live in `~/.hermes/skins/`
- active skin is read from `~/.hermes/config.yaml`

## Installation

```bash
cd ~/dev/skinwalker
uv sync
```

## Run

```bash
uv run skinwalker
```

Useful non-TUI check:

```bash
uv run skinwalker --dump-active
```

## Keybindings

- `F2`: Save
- `F3`: Activate
- `F4`: New draft
- `F5`: Generate logo
- `F6`: Generate hero
- `F7`: Refresh library
- `Ctrl+E`: Open emoji/symbol picker for the focused supported field

## Current App Layout

The TUI is organized into three panes:

1. Library pane

- built-in and custom skin list
- new, clone, refresh, delete actions

2. Center pane

- preview tab
- YAML tab
- save / save-as / activate actions
- quick access to emoji picker, logo generation, and hero generation

3. Editor pane

- identity tab
- colors tab
- spinner tab
- art tab

## Architecture Overview

Core modules:

- [src/skinwalker/app.py](/Users/maps/dev/skinwalker/src/skinwalker/app.py)
  - Textual app, layout, UI event handling, draft state, save/activate flows
- [src/skinwalker/hermes.py](/Users/maps/dev/skinwalker/src/skinwalker/hermes.py)
  - bridge into Hermes skin/config behavior
- [src/skinwalker/model.py](/Users/maps/dev/skinwalker/src/skinwalker/model.py)
  - skin normalization, palette/spinner presets, parsing helpers
- [src/skinwalker/art.py](/Users/maps/dev/skinwalker/src/skinwalker/art.py)
  - logo generation, art import, and current hero generation
- [src/skinwalker/preview.py](/Users/maps/dev/skinwalker/src/skinwalker/preview.py)
  - terminal-native preview rendering
- [src/skinwalker/__main__.py](/Users/maps/dev/skinwalker/src/skinwalker/__main__.py)
  - CLI entry point

## Repository Layout

- [src/](/Users/maps/dev/skinwalker/src)
  - Python package
- [ROADMAP.md](/Users/maps/dev/skinwalker/ROADMAP.md)
  - high-level phased roadmap
- [SKINWALKER_UPGRADE_PLAN.md](/Users/maps/dev/skinwalker/SKINWALKER_UPGRADE_PLAN.md)
  - detailed implementation plan
- [ASCII_TEXT_TUI_SPEC.md](/Users/maps/dev/skinwalker/ASCII_TEXT_TUI_SPEC.md)
  - local text-to-ASCII tool spec
- [ASCIIWALKER_STANDALONE_SPEC.md](/Users/maps/dev/skinwalker/ASCIIWALKER_STANDALONE_SPEC.md)
  - standalone text generator parity plan
- [IMAGE_TO_ASCII_STANDALONE_SPEC.md](/Users/maps/dev/skinwalker/IMAGE_TO_ASCII_STANDALONE_SPEC.md)
  - standalone and integrated image-to-ASCII plan

## Known Limitations

Current known limitations include:

- no repository test suite yet
- no app-level undo/redo
- the current font browser is searchable but still flat
- the hero generator is intentionally first-pass and much smaller than the planned image lab
- preview fidelity is useful but not exhaustive for all Hermes runtime states
- duplicate visible names in user skin YAML can still create confusing library rows until the planned bridge cleanup lands

## Roadmap

The current roadmap intentionally avoids spending effort on adding more built-in palette schemes. The existing palette catalog is considered sufficient for now; the work is on organization and usability.

### Phase 1: Foundation

- add tests for normalization, bridge behavior, generators, and app state
- fix duplicate library names and other library edge cases
- separate persisted draft state from transient generator state
- add whole-skin YAML import/export
- add profile-aware activation and profile targeting
- add diagnostics for validation, save, and import issues

### Phase 2: Workflow And UX

- app-level undo/redo
- better keyboard navigation
- per-field select-all, clear, and reset affordances
- section-level actions for palette, spinner, logo, and hero areas
- modified-field and modified-section highlighting
- active-vs-draft diff view
- autosave and recovery snapshots

### Phase 3: Color UX

- palette browser with preview-before-apply
- palette categorization and tags for the existing built-ins
- per-field color picker
- contrast/readability warnings
- reset-to-preset and "modified from preset" indicators
- stronger palette import/export UX

### Phase 4: Font System

- categorized font browser
- live preview for the highlighted font
- preview-all mode for the current filtered set
- favorites and recents
- clearer separation between generator controls and applied banner markup

### Phase 5: Hero / Image Lab

- richer image-to-ASCII engine
- source-image preview
- crop/fit/pad support
- filter controls such as contrast, invert, threshold, sharpen, and edge detection
- gradient and dithering options
- apply/export flows

### Phase 6: AI-Assisted Generation

- Hermes-first generation backend
- env-key fallbacks when Hermes is unavailable
- structured suggestion output for branding, spinner bundles, and art prompts
- explicit accept/apply flow rather than silent mutation

## Design Direction

The near-term product direction is:

- keep it terminal-native
- make large text editing feel much less punishing
- improve preview confidence before save/activate
- support profile-aware Hermes workflows
- make art generation feel like a real lab, not a small helper panel
- keep AI assistive and controlled

## Notes

- Built-in skins are read from Hermes' Python skin engine.
- Custom skin names may not shadow built-in skin names.
- The preview is terminal-native on purpose and does not try to reproduce a browser UI.
- Text and image ASCII generation planning lives in the spec files listed above.
