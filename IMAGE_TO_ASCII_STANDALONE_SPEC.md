# Image To ASCII Standalone And Integration Spec

## Goal

Build a local version of the `Image to ASCII Art` tool at:

- https://www.asciiart.eu/image-to-ascii

This should work in two forms:

1. standalone local tool
2. integrated Skinwalker image/hero generator

## Verdict

This is feasible as a TUI and as a local app.

Unlike the text generator, this tool does not depend on a special rendering engine like `figlet.js`. The live site uses a custom JavaScript canvas pipeline with local filter logic, dithering, edge detection, and text export. That maps cleanly to a local Python implementation.

Recommendation:

- standalone engine: Python
- standalone UI: `textual`
- integration target: Skinwalker hero/image lab

## Reverse-Engineered Findings

From the live page and source:

- the page supports drag/drop or file-select upload
- output width is controlled by a `Characters` slider
- it has brightness, contrast, saturation, hue, grayscale, sepia, and invert controls
- thresholding is toggleable with a threshold offset slider
- sharpening is toggleable with a sharpness slider
- edge detection is toggleable with an edge intensity slider
- there are named ASCII gradient presets
- there is a space-density control
- there is a transparent-frame control
- quality enhancements are implemented as dithering modes
- export options include clipboard copy, text save, and PNG save
- the page credits ClipboardJS and Bootstrap, and otherwise describes the tool as their own JavaScript implementation

## Site Feature Surface

Observed controls:

- `Characters`: 20 to 400
- `Brightness`: 0 to 200
- `Contrast`: 0 to 200
- `Saturation`: 0 to 400
- `Hue`: 0 to 360
- `Grayscale`: 0 to 100
- `Sepia`: 0 to 100
- `Invert Colors`: 0 to 100
- `Thresholding`: toggle + `Threshold Offset` 0 to 255
- `Sharpness`: toggle + `Sharpness` 1 to 20
- `Edge Detection`: toggle + `Edge Intensity` 0 to 2
- `Space Density`: 0 to 40
- `Transparent Frame`: 0 to 10 px

Observed ASCII gradients:

- `alphabetic`
- `alphanumeric`
- `arrow`
- `codepage437`
- `extended`
- `grayscale`
- `minimalist`
- `math`
- `normal`
- `normal2`
- `numerical`
- `max`
- `blockelement`

Observed quality-enhancement modes:

- `none`
- `FloydSteinberg`
- `JJN`
- `Stucki`
- `Atkinson`

Observed implementation details from source:

- the site converts the source image onto a canvas
- it applies browser filter controls for brightness / contrast / saturation / sepia / hue / grayscale / invert
- it optionally applies custom edge detection
- it optionally applies custom sharpening
- it optionally applies simple thresholding
- it maps luminance to a chosen ASCII gradient
- it optionally applies dithering before character selection
- it renders a separate preview canvas and separate ASCII text output
- it exports TXT and PNG locally in-browser

## Comparison To Current Skinwalker

Skinwalker already has a simpler hero generator in [art.py](/Users/maps/dev/skinwalker/src/skinwalker/art.py#L191) and [art.py](/Users/maps/dev/skinwalker/src/skinwalker/art.py#L271).

Current Skinwalker hero generation:

- accepts an image path
- converts to grayscale
- runs autocontrast + sharpen
- supports four output styles: `braille`, `ascii`, `blocks`, `dots`
- supports width plus justify/fixed-width formatting
- outputs Rich markup for `banner_hero`

Current gaps versus the site:

- no brightness control
- no contrast control beyond autocontrast
- no saturation / hue / sepia / grayscale mix / invert controls
- no thresholding control
- no explicit sharpen toggle or amount UI beyond fixed internal sharpen
- no edge detection
- no dithering modes
- no named multi-gradient browser beyond four hardcoded styles
- no transparent frame
- no source-image preview pane
- no export surface beyond injecting hero markup into a skin

That means this should not be treated as a small patch. It should be a shared engine that Skinwalker consumes.

## Recommended Product Shape

### Standalone

Primary recommendation:

- package name: `imagewalker`

Optional longer-term suite unification:

- `asciiwalker text`
- `asciiwalker image`

I would still start with a dedicated standalone image tool because the control surface is large enough to deserve its own UX.

### Skinwalker Integration

Add a dedicated `Image Lab` or `Hero Lab` workflow inside Skinwalker:

- open image
- adjust filters
- choose gradient
- choose dithering
- choose output width and fit mode
- preview final terminal block
- apply directly to `banner_hero`

## Architecture

### Core Engine

Implement a pure Python rendering core with Pillow as the base image library.

Recommended modules:

- `src/imagewalker/engine.py`
- `src/imagewalker/filters.py`
- `src/imagewalker/dither.py`
- `src/imagewalker/gradients.py`
- `src/imagewalker/export.py`
- `src/imagewalker/app.py`

Suggested optional dependencies:

- `numpy` for faster pixel operations
- `Pillow` for image loading, resizing, and PNG export

The engine should be UI-agnostic.

### Render Pipeline

Recommended order:

1. load image
2. normalize orientation via EXIF
3. optional crop / fit / pad
4. resize to target character width
5. apply color/filter adjustments
6. optional edge detection
7. optional sharpen
8. optional thresholding
9. optional dithering
10. map luminance to gradient characters
11. apply space-density policy
12. apply transparent frame or padding
13. align within fixed or flexible width
14. emit plain text or Rich-markup output

The output should preserve a raw text representation and a styled preview representation separately.

## Data Model

```python
@dataclass
class ImageAsciiRequest:
    image_path: str
    characters: int
    brightness: int
    contrast: int
    saturation: int
    hue: int
    grayscale: int
    sepia: int
    invert: int
    threshold_enabled: bool
    threshold_offset: int
    sharpen_enabled: bool
    sharpness: float
    edge_enabled: bool
    edge_intensity: float
    gradient: str
    dithering: str
    space_density: int
    transparent_frame: int
    justify: str
    fit_mode: str
    color_mode: str
```

```python
@dataclass
class ImageAsciiResult:
    plain_text: str
    rich_markup: str
    width: int
    height: int
    overflow: bool
    warnings: list[str]
```

## Gradient System

The site hardcodes named character gradients in source.

Local clone recommendation:

- vendor the site-compatible named gradients as the default set
- add custom gradient editing in phase two
- keep gradient definitions in a dedicated table

Suggested file:

- `src/imagewalker/gradients.py`

This should include at least:

- `minimalist`
- `normal`
- `normal2`
- `alphabetic`
- `alphanumeric`
- `numerical`
- `extended`
- `math`
- `arrow`
- `grayscale`
- `max`
- `codepage437`
- `blockelement`

## Filter System

Map site behavior into Python transforms:

- brightness: multiply luminance or RGB channels
- contrast: center around midtone and scale
- saturation: convert through HSL/HSV or matrix transform
- hue: hue rotation in HSV/HSL space
- grayscale: mix original with grayscale version
- sepia: matrix transform
- invert: mix original with inverted version

These are deterministic and fully feasible locally.

## Dithering System

Implement the named modes directly:

- Floyd-Steinberg
- Jarvis, Judice and Ninke
- Stucki
- Atkinson

These should operate on grayscale luminance before character mapping.

Recommendation:

- pure Python implementation first
- add `numpy` acceleration if performance becomes a problem

## Edge Detection And Sharpen

The site uses custom pixel operations for both.

Local recommendation:

- edge detection: Sobel operator on luminance
- sharpening: configurable convolution kernel

Expose both as toggles with intensity sliders so the Skinwalker integration can match the standalone tool.

## TUI Design

Recommended three-pane layout:

1. Source pane

- file path
- image metadata
- crop/fit mode
- optional tiny Unicode block preview of the source image

2. Controls pane

- grouped selectors and sliders for all filter settings
- gradient selector
- dithering selector
- width / fit / justify
- presets

3. Output pane

- live ASCII output
- dimensions
- overflow warnings
- export actions

## Smart Wrapping

This matters in a TUI because terminal soft-wrap will destroy readability.

Rules:

- never let the terminal emulator wrap the ASCII block implicitly
- render to an off-screen string first
- measure block width
- if wider than the pane:
  - keep raw output unchanged
  - show a horizontal-scroll preview or clipped preview
  - warn the user
  - offer auto-fit suggestions

For Skinwalker specifically:

- keep the stored `banner_hero` raw and unchanged
- only clip or scroll in preview

## Export

Standalone export actions:

- copy to clipboard
- save `.txt`
- save `.ansi.txt` if styled mode exists later
- save `.png`

On this machine, clipboard copy should use:

- `pbcopy`

PNG export should use Pillow with a selectable monospace font and font size.

## Color Modes

The site outputs plain monochrome ASCII text.

For local tooling, support two output modes:

1. plain text

- exact ASCII output
- ideal for clipboard, files, and parity mode

2. styled text

- Rich-markup tinted output
- ideal for Skinwalker hero banners

This is where standalone and integration diverge cleanly:

- standalone defaults to plain text parity
- Skinwalker defaults to styled hero output using the current skin accent color

## Integration Plan For Skinwalker

### Phase 1

Extract the current hero generation into a reusable shared engine boundary.

Then replace the direct hero generator UI in [app.py](/Users/maps/dev/skinwalker/src/skinwalker/app.py#L412) with an `Image Lab` backed by the new engine.

### Phase 2

Expose the site-compatible controls:

- characters
- brightness
- contrast
- saturation
- hue
- grayscale
- sepia
- invert
- thresholding
- sharpness
- edge detection
- gradient
- dithering
- space density
- transparent frame
- justify
- fixed vs flexible width

### Phase 3

Add integration niceties:

- hero presets per skin
- save/load image-lab presets
- per-skin default hero pipeline
- direct `Apply To Banner Hero`
- optional `Apply To Banner Logo` for special use cases

## Presets

Useful default preset families:

- `photo-soft`
- `line-art`
- `matrix-terminal`
- `amber-phosphor`
- `braille-dense`
- `posterized`
- `edge-outline`

This will matter more in Skinwalker than on the site, because the user is shaping a reusable skin identity rather than doing one-off conversion.

## What Is Hard Versus Easy

Easy:

- pure local image conversion
- all site sliders and toggles
- site dithering modes
- site gradient names
- clipboard and text export
- PNG export
- integration into `banner_hero`

Medium:

- fast performance on large images without `numpy`
- pleasant source-image preview in a plain TTY
- making the very large control surface feel good in Textual

Hard:

- exact visual parity with browser canvas filtering in every edge case
- rich raster preview inside every terminal type

Those hard parts are not blockers.

## If TUI Feels Too Tight

If you later want a more visual image workflow, a local desktop/web app is also straightforward because the core engine is pure Python and reusable.

That fallback would be useful for:

- side-by-side source and rendered image preview
- crop-box editing
- visual region selection

But it is not required to make this useful.

## Recommended Build Order

1. Build `imagewalker` core engine first.
2. Match the site feature surface in parity mode.
3. Add Textual standalone UI.
4. Add clipboard / text / PNG export.
5. Integrate the engine into Skinwalker as `Image Lab`.
6. Replace the current simplified hero generator path.

## Bottom Line

This should be built as a standalone first and then integrated into Skinwalker.

Unlike the text generator, this one does not need a special external rendering engine for fidelity. A pure Python engine can recreate nearly all of the website's behavior, and then Skinwalker can consume that engine to turn its current basic hero generator into a much more capable image-to-banner workflow.
