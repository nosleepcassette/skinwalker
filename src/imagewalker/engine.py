from __future__ import annotations

from dataclasses import dataclass, field

from PIL import ImageOps
from rich.markup import escape

from skinwalker.art import (
    HERO_STYLE_MAP,
    _load_image,
    _prepare_image,
    _render_braille,
    _render_ramp,
    _render_ramp_dithered,
)

MIN_CHARACTERS = 20
MAX_CHARACTERS = 400
JUSTIFY_OPTIONS = {"left", "center", "right"}
FIT_MODE_OPTIONS = {"flexible", "fixed"}
DITHER_ALIASES = {
    "none": "none",
    "floyd-steinberg": "floyd-steinberg",
    "floydsteinberg": "floyd-steinberg",
    "atkinson": "atkinson",
    "jjn": "jjn",
    "stucki": "stucki",
}


@dataclass(frozen=True)
class ImageAsciiRequest:
    image_path: str
    characters: int = 80
    brightness: float = 100.0
    contrast: float = 100.0
    saturation: float = 100.0
    hue: float = 0.0
    grayscale: float = 100.0
    sepia: float = 0.0
    invert: float = 0.0
    threshold_enabled: bool = False
    threshold_offset: int = 128
    sharpen_enabled: bool = False
    sharpness: float = 1.0
    edge_enabled: bool = False
    edge_intensity: float = 0.0
    gradient: str = "ascii"
    dithering: str = "none"
    space_density: float = 0.0
    transparent_frame: int = 0
    justify: str = "left"
    fit_mode: str = "flexible"
    color_mode: str = "plain"
    color: str = "#C8C8C8"


@dataclass(frozen=True)
class ImageAsciiResult:
    plain_text: str
    rich_markup: str
    width: int
    height: int
    overflow: bool
    warnings: list[str] = field(default_factory=list)


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _normalize_dither(value: str) -> str:
    normalized = str(value or "").strip().lower() or "none"
    if normalized not in DITHER_ALIASES:
        raise ValueError(f"Unknown dithering mode: {value}")
    return DITHER_ALIASES[normalized]


def _normalize_gradient(value: str) -> str:
    gradient = str(value or "").strip().lower() or "ascii"
    if gradient not in HERO_STYLE_MAP:
        raise ValueError(f"Unknown gradient: {value}")
    return gradient


def _normalize_justify(value: str) -> str:
    justify = str(value or "").strip().lower() or "left"
    if justify not in JUSTIFY_OPTIONS:
        raise ValueError(f"Unknown justification: {value}")
    return justify


def _normalize_fit_mode(value: str) -> str:
    fit_mode = str(value or "").strip().lower() or "flexible"
    if fit_mode not in FIT_MODE_OPTIONS:
        raise ValueError(f"Unknown fit mode: {value}")
    return fit_mode


def _markup_text(text: str, color: str) -> str:
    if not text:
        return ""
    color = str(color or "").strip()
    return f"[{color}]{escape(text)}[/]" if color else escape(text)


def _format_block(text: str, *, justify: str, fit_mode: str, width: int | None = None) -> str:
    lines = [line.rstrip() for line in str(text or "").splitlines()]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        return ""

    justify_mode = _normalize_justify(justify)
    normalized_fit_mode = _normalize_fit_mode(fit_mode)
    content_width = max(len(line) for line in lines)
    target_width = content_width
    if width is not None and normalized_fit_mode == "fixed":
        target_width = max(content_width, min(MAX_CHARACTERS, int(width)))

    formatted: list[str] = []
    for line in lines:
        if justify_mode == "left":
            formatted_line = line if normalized_fit_mode == "flexible" else line.ljust(target_width)
        elif justify_mode == "center":
            if normalized_fit_mode == "fixed":
                formatted_line = line.center(target_width)
            else:
                padding = max(0, (content_width - len(line)) // 2)
                formatted_line = (" " * padding) + line
        else:
            formatted_line = line.rjust(target_width)
        formatted.append(formatted_line)

    return "\n".join(formatted)


def _apply_transparent_frame(text: str, frame: int) -> str:
    frame_amount = max(0, int(frame))
    if frame_amount <= 0:
        return text

    horizontal_pad = max(1, round(frame_amount / 2))
    vertical_pad = max(1, round(frame_amount / 4))
    lines = text.splitlines() or [""]
    content_width = max(len(line) for line in lines)
    padded_lines = [
        (" " * horizontal_pad) + line.ljust(content_width) + (" " * horizontal_pad)
        for line in lines
    ]
    blank_line = " " * (content_width + (horizontal_pad * 2))
    return "\n".join((([blank_line] * vertical_pad) + padded_lines + ([blank_line] * vertical_pad)))


def render_source_preview(image_path: str, *, width: int = 24, height: int = 12) -> str:
    palette = " .:-=+*#%@"
    image = _load_image(image_path)
    grayscale = ImageOps.autocontrast(image.convert("L")).resize((width, height))
    rows: list[str] = []
    for y in range(height):
        chars: list[str] = []
        for x in range(width):
            value = grayscale.getpixel((x, y))
            index = round((value / 255) * (len(palette) - 1))
            chars.append(palette[index])
        rows.append("".join(chars).rstrip())
    return "\n".join(rows).strip("\n")


def render_image_ascii(request: ImageAsciiRequest) -> ImageAsciiResult:
    warnings: list[str] = []
    requested_characters = int(request.characters)
    characters = int(_clamp(requested_characters, MIN_CHARACTERS, MAX_CHARACTERS))
    if characters != requested_characters:
        warnings.append(f"Characters clamped to {characters} (supported range: {MIN_CHARACTERS}-{MAX_CHARACTERS}).")

    gradient = _normalize_gradient(request.gradient)
    dithering = _normalize_dither(request.dithering)
    justify = _normalize_justify(request.justify)
    fit_mode = _normalize_fit_mode(request.fit_mode)

    image = _load_image(request.image_path)
    processed = _prepare_image(
        image,
        brightness=_clamp(float(request.brightness), 0.0, 200.0) / 100.0,
        contrast=_clamp(float(request.contrast), 0.0, 200.0) / 100.0,
        saturation=_clamp(float(request.saturation), 0.0, 400.0) / 100.0,
        hue_shift=_clamp(float(request.hue), 0.0, 360.0),
        grayscale_blend=_clamp(float(request.grayscale), 0.0, 100.0) / 100.0,
        sepia=_clamp(float(request.sepia), 0.0, 100.0) / 100.0,
        invert=_clamp(float(request.invert), 0.0, 100.0) / 100.0,
        threshold=int(_clamp(float(request.threshold_offset), 0.0, 255.0)) if request.threshold_enabled else None,
        sharpen=max(1.0, float(request.sharpness)) if request.sharpen_enabled else 1.0,
        edge_strength=_clamp(float(request.edge_intensity), 0.0, 2.0) / 2.0 if request.edge_enabled else 0.0,
    )

    style_meta = HERO_STYLE_MAP[gradient]
    if style_meta["renderer"] == "braille":
        if dithering != "none":
            warnings.append("Dithering is ignored for braille output.")
        plain, _ = _render_braille(processed, characters)
    elif dithering != "none":
        plain, _ = _render_ramp_dithered(processed, style_meta["chars"], characters, dithering)
    else:
        density = _clamp(float(request.space_density), 0.0, 40.0) / 40.0
        plain, _ = _render_ramp(processed, style_meta["chars"], characters, density)

    plain = _format_block(plain, justify=justify, fit_mode=fit_mode, width=characters)
    plain = _apply_transparent_frame(plain, request.transparent_frame)
    width = max((len(line) for line in plain.splitlines()), default=0)
    height = len(plain.splitlines()) if plain else 0
    overflow = width > characters
    if overflow:
        warnings.append(f"Rendered width {width} exceeds requested character width {characters}.")
    rich_markup = _markup_text(plain, request.color) if request.color_mode == "styled" else escape(plain)

    return ImageAsciiResult(
        plain_text=plain,
        rich_markup=rich_markup,
        width=width,
        height=height,
        overflow=overflow,
        warnings=warnings,
    )
