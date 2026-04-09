# ASCII Text TUI Spec

## Goal

Build a local terminal-native equivalent to the `Text to ASCII Art` generator at:

- https://www.asciiart.eu/text-to-ascii-art

This should be treated as a clean-room reimplementation, not a literal code fork. The site states that its text generator is built with JavaScript and `figlet.js`, and credits FIGlet fonts/technology. A local TUI clone is feasible by reusing the same broad ideas with local rendering backends and a Textual interface.

## Verdict

Feasibility is high.

The site is mostly a FIGlet banner engine plus formatting layers:

- text input
- large font library
- layout modes
- width control
- borders and padding
- comment-style wrappers
- whitespace trimming/replacement
- copy/save/export flows

Those map well to a local TUI. The only real caveat is exact layout parity. `pyfiglet` gives strong local font coverage, but not a first-class UI for all of the site's layout mode labels. On this machine, `toilet` is installed and exposes render modes much closer to the website's behavior, so the best design is:

- primary render backend: `toilet`
- fallback backend: `pyfiglet`
- UI shell: `textual`

## Source Notes

Observed from the live page:

- the page advertises over 270 fonts
- it exposes horizontal and vertical layout controls
- it supports width, border, vertical padding, horizontal padding
- it supports comment-style wrapping
- it supports trim whitespace, whitespace break, and replace whitespace
- it supports copy, save as ASCII art, and save as image
- credits mention FIGlet and `figlet.js`

Verified locally:

- `pyfiglet` exposes 571 fonts in the current environment
- `toilet` is installed at `/usr/local/bin/toilet`
- `toilet --help` exposes render modes: default, force smushing, kerning, full width, overlap

## Product Shape

Two viable forms:

1. Standalone app

- command: `asciiwalker`
- separate repo or package
- cleaner identity and simpler UX

2. Skinwalker sidecar tool

- add a new tab or mode inside the current Textual app
- reuse the existing `textual` stack, preview panes, export conventions, and packaging

Recommendation:

- build it in the current repo first as a sidecar mode
- if it grows beyond banner generation, split it later

## User Experience

Three-pane layout:

1. Controls pane

- text input
- backend selector: `toilet` or `pyfiglet`
- font selector with filter box
- layout mode
- width
- justification
- direction
- border preset
- horizontal and vertical padding
- comment style
- trim whitespace toggle
- whitespace break toggle
- replace-space character

2. Preview pane

- live ASCII output
- dimensions: width, height, character count
- warnings when output exceeds current terminal width

3. Export pane

- raw output
- wrapped output
- save target path
- export buttons or hotkeys

Recommended key flows:

- `/` focus font search
- `tab` cycle control groups
- `enter` apply highlighted font or preset
- `F2` save text
- `F3` export image
- `F4` copy to clipboard
- `F5` toggle backend
- `F6` open presets

## Rendering Architecture

### Backend Layer

Define a backend interface:

```python
class BannerBackend(Protocol):
    def list_fonts(self) -> list[str]: ...
    def render(self, request: RenderRequest) -> str: ...
```

`RenderRequest` fields:

- `text`
- `font`
- `width`
- `layout_mode`
- `justify`
- `direction`

Backends:

1. `ToiletBackend`

- call `toilet` via subprocess
- map layout mode to flags:
  - `normal` -> default
  - `narrow` or `squeezed` -> `-s`
  - `fitted` -> `-k`
  - `wide` -> `-W`
  - `overlap` -> `-o`
- use `-w` for width
- add font directory support if needed

2. `PyfigletBackend`

- use `pyfiglet.Figlet`
- supports font, width, direction, justify
- used as fallback when `toilet` is unavailable
- acceptable for broad compatibility, but not exact layout parity

### Formatting Pipeline

After text is rendered:

1. normalize trailing newlines
2. optionally trim surrounding whitespace
3. optionally replace spaces with a chosen fill character
4. optionally hard-wrap on spaces when width is exceeded
5. optionally add comment wrapper
6. optionally add border and padding

This separation matters. The banner renderer should only produce the art. Everything else should be a deterministic post-processing pass.

## Feature Mapping

### Straightforward

- text input
- font browser and search
- width control
- left/center/right justification
- border presets
- horizontal and vertical padding
- comment wrappers
- trim whitespace
- replace spaces
- save to text file
- copy to clipboard

### Medium Complexity

- terminal-width-aware live preview
- space-break wrapping for long phrases
- saved presets
- export to image via Pillow

### Higher Complexity

- exact parity with both horizontal and vertical site layout labels
- matching every site border preset one-for-one
- WYSIWYG image export with font fidelity identical to terminal rendering

## Data Model

```python
@dataclass
class RenderRequest:
    text: str
    backend: str
    font: str
    width: int
    layout_mode: str
    justify: str
    direction: str
    border: str
    padding_x: int
    padding_y: int
    comment_style: str
    trim_whitespace: bool
    break_on_spaces: bool
    replace_space_with: str
```

```python
@dataclass
class RenderResult:
    raw_ascii: str
    wrapped_ascii: str
    warnings: list[str]
    width: int
    height: int
```

## Border and Comment System

Keep these as local presets in data tables.

Border presets:

- none
- dots
- simple
- box light
- box double
- stars
- waves
- shell
- slash frame
- brace frame

Comment presets:

- none
- `#`
- `//`
- `///`
- `--`
- `/* ... */`
- `""" ... """`
- `<!-- ... -->`
- `REM`

Each wrapper should be implemented as a pure formatting function over a rendered block.

## Export Paths

Text export:

- save `.txt`
- save `.asc`
- save `.md` fenced block

Clipboard:

- shell out to `pbcopy` on macOS

Image export:

- render the final ASCII block into a Pillow image
- configurable foreground/background colors
- monospace font selection for export only

## MVP

Build this first:

1. Textual app shell
2. `toilet` backend
3. `pyfiglet` fallback backend
4. text input
5. font browser with filter
6. width control
7. layout mode selector
8. border and padding
9. comment wrapper
10. trim whitespace and replace-space toggle
11. save to text file
12. copy to clipboard

That is enough to be genuinely useful and already competitive with the website for terminal users.

## Phase 2

- image export
- preset save/load
- recent fonts
- favorites
- batch generation from a list of phrases
- split preview: raw vs wrapped
- colorized ANSI preview mode

## Phase 3

- full preset gallery
- border editor
- live terminal-size adaptation
- integration into Skinwalker logo/banner generation workflow
- optional plugin mode so Skinwalker can open the generated text directly into `banner_logo`

## Risks

1. Exact layout parity is the main uncertainty.

The site exposes both horizontal and vertical layout controls with user-friendly names. `toilet` gets close, but a one-to-one mapping may still need testing and documentation.

2. Font names differ across engines.

The same conceptual FIGlet font set may have naming differences between `toilet`, `pyfiglet`, and the website.

3. Image export is inherently approximate.

Terminal preview, clipboard output, and rendered PNG output are different mediums.

## Implementation Recommendation

If the goal is speed:

- keep it in `~/dev/skinwalker`
- add `src/skinwalker/ascii_tui.py`
- add a new script entrypoint such as `asciiwalker`
- reuse the current Textual app patterns, modals, status bar, and preview components

If the goal is product clarity:

- create a sibling repo after the MVP works

## Rough Build Plan

1. Add render backends and a pure formatting pipeline.
2. Add a minimal Textual app with text, font, width, and preview.
3. Add layout mode mapping for `toilet`.
4. Add borders, padding, and comment wrappers.
5. Add save and clipboard export.
6. Add image export.
7. Add presets and Skinwalker integration.

## Bottom Line

A local TUI equivalent is absolutely feasible.

It is better framed as a clean local reimplementation than a literal fork. The fastest strong version uses `toilet` for rendering fidelity, `pyfiglet` as fallback, and `textual` for the TUI. If built inside the current repo, it can also become a direct banner/logo generator for Skinwalker with very little wasted work.
