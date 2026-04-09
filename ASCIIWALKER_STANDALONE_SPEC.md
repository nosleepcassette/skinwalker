# Asciiwalker Standalone Spec

## Goal

Build a standalone local clone of the `Text to ASCII Art` function at:

- https://www.asciiart.eu/text-to-ascii-art

The standalone should run as a TUI first, then be embeddable into Skinwalker once stable.

## Verdict

This is feasible as a TUI.

It is not a browser-only problem. The site is fundamentally:

- a FIGlet text renderer
- a font library and dropdown taxonomy
- layout mode controls
- frame and padding post-processing
- preview and export helpers

All of that can be recreated locally. The cleanest high-fidelity path is to use a local Node helper with `figlet.js` for rendering parity and a Python `textual` front end for the TUI shell.

## Reverse-Engineered Findings

From the live page source:

- the site says it is built by their team in JavaScript and Bootstrap
- it credits FIGlet and `figlet.js`
- it loads `/script/figlet.min.js`
- it calls `figlet.defaults({fontPath:"assets/fonts"})`
- it preloads `Standard` and `Ghost`
- it binds live regeneration to every key option change
- it uses `clipboard.js` for copy-to-clipboard
- it uses an inline `AsciiExport` canvas renderer for PNG, JPG, and GIF export
- it uses an inline `FrameHelper` implementation for borders
- it fetches `preview all` content from `/app/tools/text-to-ascii/preview-all.php`

## Site Feature Inventory

Observed directly in the page source:

- 279 font options
- 17 font groups
- 5 horizontal layout values
- 5 vertical layout values
- 38 border designs
- vertical padding 0-5
- horizontal padding 0-5
- whitespace break toggle
- trim whitespace toggle
- replace-space character input
- comment/output wrapping presets
- output preview font family selector
- output preview font size selector
- text export
- image export
- clipboard copy

## Local Compatibility Findings

Verified locally in this repo environment:

- `pyfiglet` exposes 571 fonts
- a normalization pass already matches 269 of the site's 279 dropdown fonts
- `node` is installed
- `npm` is installed
- `pbcopy` is available for macOS clipboard integration

The 10 fonts not matched by the local `pyfiglet` package name set are:

- `Patorjks Cheese`
- `Small Isometric1`
- `Banner3-D`
- `Caligraphy2`
- `Peaks Slant`
- `Reverse`
- `Small Tengwar`
- `Small Keyboard`
- `Efti Italic`
- `Small Script`

Most of these are available directly from the public `figlet.js` font set. The only notable alias issue found so far is:

- site dropdown label: `Patorjks Cheese`
- public font asset name: `Patorjk's Cheese.flf`

That means full dropdown parity looks like an asset-vendoring and alias-mapping task, not a hard technical blocker.

## Recommended Architecture

### Front End

Use `textual` for the standalone TUI.

Recommended layout:

- left pane: controls
- center pane: live preview
- right pane: metadata, wrapped output, export actions

### Render Engine

Primary engine:

- local Node helper using official `figlet.js`

Why:

- it matches the website's render engine family directly
- it supports the same layout vocabulary
- it removes most parity guesswork

Suggested shape:

- `renderer/render.mjs`
- input: JSON on stdin or argv
- output: rendered ASCII on stdout

Secondary fallback:

- Python `pyfiglet`

Why:

- strong offline fallback
- huge local font coverage
- good enough when Node is unavailable

### Font Assets

Use the site dropdown as the canonical font menu.

Recommended process:

1. Parse the live dropdown once into a local manifest.
2. Map each display name to a local asset name.
3. Vendor any missing `.flf` files from the public `figlet.js` / FIGlet font set.
4. Keep aliases for site-label mismatches such as `Patorjks Cheese`.

Store locally:

- `assets/font-manifest.json`
- `assets/fonts/*.flf`

## Why TUI Still Works

The main concern is avoiding broken wrapping or squashed output. That is solvable.

The TUI should never hard-wrap the rendered ASCII block by the terminal emulator. Instead it should:

1. render to an internal string buffer
2. measure block width and height
3. compare against terminal size
4. decide one of these strategies before display:

- render as-is
- warn about overflow
- auto-increase generation width if whitespace-break is enabled
- switch preview pane to horizontal scroll mode
- clip only in preview while preserving full export text

That means the preview can stay visually correct without silently mangling the underlying art.

## Smart Wrapping Spec

Inputs:

- current terminal columns
- current terminal rows
- rendered block width
- rendered block height
- whitespace-break toggle
- fixed-width mode toggle

Rules:

- never wrap inside a rendered line after generation
- never let the terminal perform accidental soft wrap in the preview pane
- if output exceeds pane width, mark it as overflow and offer:
  - wider generation width
  - different layout mode
  - whitespace-break pass
  - scroll preview
- if fixed-width mode is enabled, pad or align within a requested width after render
- if flexible-width mode is enabled, preserve natural line length

## Preview All

The site's `Preview all` currently depends on a remote PHP endpoint.

The local clone should do this itself:

- iterate the local font manifest
- render a short sample phrase for each font
- cache the result on first request
- show it in a scrollable list with search and quick-apply

This is a straightforward local feature and should work better than the website version.

## Clipboard

Automatic clipboard copy is feasible.

Recommended behavior:

- explicit toggle: `auto-copy on render`
- explicit action: `copy now`

Platform backends:

- macOS: `pbcopy`
- Linux X11: `xclip` or `xsel`
- Wayland: `wl-copy`

For this machine specifically:

- use `pbcopy`

## Borders and Formatting

Do not scrape or reuse the site's JS directly.

Reimplement the behavior from clean local data tables:

- simple frames
- block frames
- combo frames
- comment wrappers
- padding rules
- whitespace trimming
- replace-space pass

This is low risk because the behavior is deterministic and the site implementation is already simple enough to model.

## Standalone Product Shape

Package name:

- `asciiwalker`

Recommended entrypoints:

- `asciiwalker`
- `asciiwalker --copy`
- `asciiwalker --preview-all`

Suggested modules:

- `src/asciiwalker/app.py`
- `src/asciiwalker/render_node.py`
- `src/asciiwalker/render_pyfiglet.py`
- `src/asciiwalker/frames.py`
- `src/asciiwalker/wrap.py`
- `src/asciiwalker/clipboard.py`
- `assets/font-manifest.json`
- `assets/fonts/`

## Integration Path Back Into Skinwalker

Once stable, integrate it into Skinwalker as a sidecar tool:

- use the standalone render core as a library
- expose a `Generate Banner` or `Logo Lab` action in Skinwalker
- let the generated output flow directly into `banner_logo`
- optionally add the standalone font browser as a modal instead of duplicating logic

The standalone should stay the source of truth. Skinwalker should consume it, not reimplement it again.

## What Is Hard Versus Easy

Easy:

- TUI shell
- live preview
- local preview-all
- clipboard
- text export
- canonical site font menu
- border and comment wrappers

Medium:

- exact site label-to-font alias table
- exact layout parity across all font edge cases
- image export that visually matches preview font choices

Hard:

- pixel-identical parity with the site's browser canvas export
- exact browser typography parity for image preview inside a TUI

Those hard parts are not blockers for a strong local clone.

## If TUI Proves Too Tight

If you later decide you want browser-identical image preview or a giant searchable font gallery with richer visual browsing, a simple local app is still trivial:

- same render core
- same font assets
- same manifest
- tiny local web UI or desktop shell

That would not invalidate the TUI work. The renderer and asset layer would carry over directly.

## Recommended Build Order

1. Build standalone `asciiwalker` first.
2. Vendor the canonical font manifest and missing font assets.
3. Implement the local Node `figlet.js` renderer.
4. Add TUI preview, search, and preview-all.
5. Add clipboard and text export.
6. Add optional image export.
7. Integrate into Skinwalker once stable.

## Bottom Line

This should be built as a standalone first.

The TUI version is viable and not fundamentally blocked. With a local `figlet.js` helper, vendored font assets, local preview-all, smart overflow handling, and `pbcopy`, it can recreate the website's core function closely enough to be better than the web tool for terminal use.
