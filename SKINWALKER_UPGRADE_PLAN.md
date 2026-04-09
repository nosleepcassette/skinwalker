# Skinwalker Upgrade Plan

## Goal

Turn Skinwalker from a working MVP editor into a dependable skin studio for Hermes:

- faster editing
- better long-text ergonomics
- stronger preview confidence
- profile-aware activation
- richer font and hero tooling
- optional AI-assisted content generation

This plan assumes the existing bundled palette set is sufficient. Color work should improve usability, not expand the palette catalog.

## Non-Goals

- Do not add new built-in palette themes as part of this plan.
- Do not rewrite the app as a web UI.
- Do not chase exact one-to-one parity with every control on external ASCII sites in the first pass.
- Do not let AI generation replace deterministic local rendering for logo and hero output.

## Current Product Shape

The current app already provides:

- real Hermes skin schema editing
- live preview plus YAML preview
- palette presets and palette import
- spinner preset editing
- pyfiglet logo generation
- first-pass image-to-ASCII hero generation
- save, save as, activate, clone, delete, and dirty-draft guards

The biggest current gaps are:

- no app-level undo/redo
- awkward large-text editing
- flat font browsing
- limited preview fidelity
- no explicit profile targeting in the UI
- no whole-skin YAML import/export flow
- no contrast linting or color picker
- no advanced image lab
- no tests in this repository

## Product Decisions

### 1. Keep Palette Expansion Out Of Scope

The app already ships multiple useful schemes. The right next step is:

- categorize what exists
- preview it better
- make overrides easier
- warn about low-contrast combinations

### 2. Separate Draft State From Tool State

Generator controls should not be treated as persisted skin values unless the user applies them.

Examples:

- logo title, width, filter, and font browser state
- hero image path and temporary filter controls
- AI prompt drafts and generation variants

Persisted skin fields remain:

- identity
- colors
- spinner
- branding
- tool prefix and tool emojis
- banner logo markup
- banner hero markup

### 3. Make Profile Targeting Explicit

Saving a skin and activating a skin are different actions and may target different profile contexts.

The UI should let the user choose:

- storage target
- activation target
- whether to affect only the current profile or another profile

### 4. Use AI As A Suggestion Layer

AI should generate proposals, not mutate the draft silently.

Every AI flow should:

- show prompt + backend used
- return structured suggestions
- preview the changes
- require explicit accept/apply

## Proposed Architecture Changes

## New Modules

- `src/skinwalker/state.py`
- `src/skinwalker/history.py`
- `src/skinwalker/palette.py`
- `src/skinwalker/fonts.py`
- `src/skinwalker/image_lab.py`
- `src/skinwalker/ai.py`
- `src/skinwalker/validation.py`

These can start small and pull logic out of `app.py` over time.

## Suggested Data Structures

```python
@dataclass
class DraftSession:
    draft: dict
    reference_draft: dict
    dirty: bool
    selected_palette: str | None
    selected_profile: str
    generator_state: GeneratorState
```

```python
@dataclass
class GeneratorState:
    logo_title: str = ""
    logo_width: int = 120
    logo_font: str = "standard"
    logo_filter: str = ""
    hero_path: str = ""
    hero_width: int = 40
    hero_style: str = "braille"
```

```python
@dataclass
class HistoryEntry:
    label: str
    draft: dict
```

```python
@dataclass
class PaletteMeta:
    name: str
    family: str
    tags: tuple[str, ...]
    colors: dict[str, str]
```

```python
@dataclass
class FontMeta:
    name: str
    category: str
    tags: tuple[str, ...]
    aliases: tuple[str, ...] = ()
```

## Phase 1: Foundation

## 1.1 Testing

Add repository tests before major feature work.

Minimum targets:

- `model.py`
  - normalization
  - color parsing
  - wing parsing
  - palette import parsing
- `hermes.py`
  - list/save/delete behavior
  - config patching
  - duplicate-name handling
  - profile-targeted activation
- `art.py`
  - logo generation normalization
  - hero width/style formatting
- app state helpers
  - history transitions
  - dirty-state behavior
  - import/export semantics

Recommended structure:

- `tests/test_model.py`
- `tests/test_hermes.py`
- `tests/test_art.py`
- `tests/test_history.py`

## 1.2 Duplicate Library Names

Current issue:

- multiple YAML files can expose the same visible `name`
- the library pane then shows duplicates with no filename/path distinction

Fix:

- de-duplicate by visible skin name at the bridge layer
- surface path or filename for collisions
- optionally mark backups as secondary entries

Preferred rule:

- canonical entry: exact filename match to `name`
- non-canonical duplicates: show as collision warnings in diagnostics

## 1.3 Whole-Skin YAML Import / Export

Add:

- import from path
- import from pasted YAML
- export current draft to chosen path
- open imported YAML as draft without immediately saving

Import modes:

- replace current draft
- merge into current draft
- save as new skin

## 1.4 Profile-Aware Operations

Add a small profile model on top of Hermes:

- discover profiles from `~/.hermes/profiles`
- resolve the effective `config.yaml`
- apply activation to the chosen profile
- show active profile and active skin in meta

Required UI:

- `Current profile`
- `Activation target`
- `Use profile config`

## 1.5 Diagnostics Surface

Add a diagnostics panel or modal that reports:

- invalid color tokens
- duplicate skin names
- missing files for imports
- save failures
- activation failures
- contrast warnings

## Phase 2: Workflow And UX

## 2.1 App-Level Undo / Redo

Widget-local undo is not enough.

Need:

- `Ctrl+Z` undo
- `Ctrl+Y` redo
- operation labels such as `Apply palette`, `Import hero`, `Edit prompt symbol`

History should be transaction-based, not per-keystroke for every field.

Suggested batching rules:

- text edits coalesce during active typing
- button-driven actions commit immediately
- import/generate actions commit as single history entries

## 2.2 Long-Text Editing Ergonomics

Add:

- focused `Select All`
- focused `Clear`
- focused `Reset`
- field-local clear buttons on large text inputs
- section-local clear buttons for spinner/logo/hero areas

Recommended targets:

- `TextArea` fields
- file path inputs
- import text boxes
- banner logo and banner hero blocks

## 2.3 Navigation

Add:

- quick jump between tabs
- jump to next modified field
- jump to next error
- search/filter in library
- section shortcuts

## 2.4 Modified-State Visibility

Highlight:

- modified fields
- modified sections
- overridden colors relative to selected palette
- generated-but-not-applied tool state

## 2.5 Diff View

Add an `Active vs Draft` tab showing:

- key/value differences
- changed colors
- changed spinner lines
- changed branding values
- changed markup blocks

## 2.6 Autosave / Recovery

Store draft snapshots under a local Skinwalker state dir.

Required behaviors:

- recover unsaved draft after crash
- show timestamped recovery options
- clear stale recovery after successful save

## Phase 3: Color UX

This phase improves usability without adding new built-in schemes.

## 3.1 Palette Browser

Replace the single flat selector with:

- category list
- live swatch row
- preview-before-apply
- palette details panel

Useful categories can be derived from the existing set:

- warm
- cool
- mono
- phosphor
- neon

These are labels, not new palettes.

## 3.2 Per-Field Color Picker

Add a color picker modal with:

- hex input
- RGB sliders
- hue/lightness/saturation sliders
- live preview of affected UI role
- copy current / revert buttons

## 3.3 Readability Checks

Warn on weak contrast for:

- banner border vs background
- banner text vs banner body
- prompt vs surrounding UI
- response border vs response label/text

Warnings should be advisory, not blocking.

## 3.4 Preset Tracking

Track:

- selected source palette
- which fields differ from that palette
- reset field to palette
- reset all fields to palette

## Phase 4: Font System

## 4.1 Font Catalog Metadata

The current font surface is large enough to require organization.

Add local metadata for:

- category
- aliases
- suggested use
- preview sample text
- favorites / recents

Suggested categories:

- featured
- clean
- compact
- block
- shadow-3d
- retro
- decorative
- novelty

## 4.2 Live Font Preview

When the highlighted font changes:

- render the preview sample immediately
- show width and height
- optionally warn when the output is too wide

Do not render all fonts at once by default.

## 4.3 Preview-All Mode

Add a dedicated preview mode for the filtered result set only.

This should:

- page through visible fonts
- cache generated previews
- allow quick apply

## 4.4 Generator / Persisted Art Split

The current art tab mixes:

- generator inputs
- import helpers
- persisted markup output

Split this into clearer sub-sections or sub-tabs:

- `Logo Lab`
- `Hero Lab`
- `Applied Art`

## Phase 5: Hero / Image Lab

## 5.1 New Engine

The current hero generator is too small for the desired feature set.

Build a shared engine with:

- source image load
- orientation fix
- crop / fit / pad
- brightness
- contrast
- saturation
- hue
- grayscale mix
- sepia
- invert
- threshold
- sharpen
- edge detection
- gradient selection
- dithering mode
- frame/padding

## 5.2 UI Surface

Add a dedicated `Hero Lab` flow:

- source image preview
- render controls
- output preview
- dimensions and overflow metadata
- apply / export / copy actions

## 5.3 Output Modes

Support:

- plain text output
- Rich-markup output for Skinwalker preview
- export to `.txt`
- optional image export later

## 5.4 Gradient Catalog

Keep gradients as named data.

Initial categories:

- minimal
- classic
- dense
- block
- braille
- dots
- math
- experimental

## Phase 6: AI-Assisted Generation

## 6.1 Backend Order

Preferred order:

1. Hermes agent or Hermes-backed local integration
2. OpenAI if `OPENAI_API_KEY` is available
3. OpenRouter if `OPENROUTER_API_KEY` is available
4. Google if `GOOGLE_API_KEY` is available

If no backend is available:

- hide generation actions or mark them unavailable
- keep deterministic local tools usable

## 6.2 AI Tasks Worth Supporting

- branding bundle
  - agent name
  - welcome
  - goodbye
  - response label
  - prompt symbol
  - help header
- spinner bundle
  - waiting faces
  - thinking faces
  - thinking verbs
  - wing pairs
- logo concept prompt
- hero concept prompt
- palette tuning suggestions based on an existing palette
- YAML import cleanup suggestions

## 6.3 Output Contract

Every AI action should return structured JSON.

Example:

```json
{
  "branding": {
    "agent_name": "Tape Deck",
    "welcome": "Magnetic memory online.",
    "goodbye": "Rewinding.",
    "response_label": " Tape Deck ",
    "prompt_symbol": ">> ",
    "help_header": "Available Commands"
  },
  "reasoning": "Warm, archival tone with concise prompt symbol."
}
```

## 6.4 Acceptance Rules

- never auto-apply silently
- always show diff before apply
- allow partial apply by subsection
- capture backend and model metadata in status text

## Suggested Delivery Order

## Milestone A

- tests
- duplicate-name fix
- whole-skin YAML import/export
- diagnostics surface

## Milestone B

- app-level undo/redo
- select-all / clear / reset improvements
- modified-field highlighting
- diff view

## Milestone C

- profile selector
- profile-targeted activation
- autosave / recovery

## Milestone D

- palette browser
- color picker
- contrast warnings
- preset tracking

## Milestone E

- categorized font browser
- live preview
- preview-all mode
- cleaner art workflow split

## Milestone F

- new hero engine
- hero lab
- export/apply flows

## Milestone G

- Hermes-first AI generation
- backend fallbacks
- structured suggestion workflow

## Acceptance Criteria

The upgrade should be considered successful when:

- users can edit large text blocks without fighting the UI
- every edit path is undoable
- library collisions are understandable and safe
- profile targeting is explicit and trustworthy
- palettes are easier to browse and override
- fonts are navigable without memorizing names
- hero generation is materially stronger than the current four-style tool
- AI actions are useful but never surprising
- the repo has enough tests to refactor safely

## Immediate Next Build Targets

If implementation starts now, the first concrete tasks should be:

1. Add tests for `model.py`, `hermes.py`, and `art.py`
2. Fix duplicate library naming in `HermesBridge.list_user_skins`
3. Add a dedicated state/history layer
4. Add whole-skin YAML import/export
5. Add profile selection and profile-targeted activation
6. Add app-level undo/redo
7. Add per-field clear/select-all/reset for large text fields
