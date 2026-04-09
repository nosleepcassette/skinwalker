from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps
from pyfiglet import Figlet, FigletFont
from rich.markup import escape

from .model import FIGLET_STYLE_MAP


@dataclass(frozen=True)
class LogoResult:
    plain: str
    markup: str
    font: str
    width: int
    height: int


@dataclass(frozen=True)
class HeroResult:
    markup: str
    style: str
    width: int
    height: int


HERO_STYLE_MAP = {
    "braille": {"renderer": "braille"},
    "ascii": {"renderer": "ramp", "chars": " .'`^\",:;Il!i~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"},
    "blocks": {"renderer": "ramp", "chars": " ░▒▓█"},
    "dots": {"renderer": "ramp", "chars": " .·•●"},
    "minimal": {"renderer": "ramp", "chars": " .:-=+*#%@"},
    "dense": {"renderer": "ramp", "chars": " .'`^\",:;Il!i~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"},
}

BRAILLE_BIT_GRID = [
    [0x01, 0x08],
    [0x02, 0x10],
    [0x04, 0x20],
    [0x40, 0x80],
]

JUSTIFY_MAP = {"left": "left", "center": "center", "right": "right"}
FIT_MODE_MAP = {"flex": "flexible", "flexible": "flexible", "fixed": "fixed"}


def build_rich_block(text: str, color: str, *, bold: bool = False, dim: bool = False) -> str:
    cleaned = text.rstrip()
    if not cleaned:
        return ""

    styles = [part for part in ("bold" if bold else "", "dim" if dim else "", color) if part]
    style = " ".join(styles).strip()
    return f"[{style}]{escape(cleaned)}[/]" if style else escape(cleaned)


@lru_cache(maxsize=1)
def list_logo_fonts() -> list[str]:
    preferred = [
        "standard",
        "slant",
        "small",
        "doom",
        "big",
        "banner",
        "banner3-d",
        "lean",
        "univers",
        "roman",
        "cyberlarge",
        "shadow",
        "ghost",
    ]
    fonts = sorted(FigletFont.getFonts(), key=str.lower)
    preferred_available = [font for font in preferred if font in fonts]
    return preferred_available + [font for font in fonts if font not in preferred_available]


def _normalize_justify(value: str) -> str:
    justify = str(value or "").strip().lower() or "left"
    if justify not in JUSTIFY_MAP:
        raise ValueError(f"Unknown justification: {value}")
    return JUSTIFY_MAP[justify]


def _normalize_fit_mode(value: str) -> str:
    fit_mode = str(value or "").strip().lower() or "flexible"
    if fit_mode not in FIT_MODE_MAP:
        raise ValueError(f"Unknown fit mode: {value}")
    return FIT_MODE_MAP[fit_mode]


def _clamp_output_width(width: int, *, minimum: int = 16, maximum: int = 200) -> int:
    return max(minimum, min(maximum, int(width)))


def _format_generated_block(text: str, *, justify: str = "left", fit: str = "flexible", width: int | None = None) -> str:
    lines = [line.rstrip() for line in str(text or "").splitlines()]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        return ""

    justify_mode = _normalize_justify(justify)
    fit_mode = _normalize_fit_mode(fit)
    content_width = max(len(line) for line in lines)
    target_width = content_width
    if width is not None and fit_mode == "fixed":
        target_width = max(content_width, _clamp_output_width(width))

    formatted: list[str] = []
    for line in lines:
        if justify_mode == "left":
            formatted_line = line if fit_mode == "flexible" else line.ljust(target_width)
        elif justify_mode == "center":
            if fit_mode == "fixed":
                formatted_line = line.center(target_width)
            else:
                padding = max(0, (content_width - len(line)) // 2)
                formatted_line = (" " * padding) + line
        else:
            formatted_line = line.rjust(target_width)
        formatted.append(formatted_line)

    return "\n".join(formatted)


def resolve_logo_font(style: str) -> str:
    raw_style = str(style or "").strip()
    if not raw_style:
        return FIGLET_STYLE_MAP["minimal"]

    alias = FIGLET_STYLE_MAP.get(raw_style.lower())
    if alias:
        return alias

    available = set(list_logo_fonts())
    candidates = [
        raw_style,
        raw_style.lower(),
        raw_style.lower().replace(" ", "_"),
        raw_style.lower().replace(" ", "-"),
        raw_style.lower().replace("-", "_"),
        raw_style.lower().replace("_", "-"),
    ]
    for candidate in candidates:
        if candidate in available:
            return candidate

    raise ValueError(f"Unknown figlet style: {style}")


def generate_logo_result(
    title: str,
    style: str,
    color: str,
    *,
    width: int = 120,
    justify: str = "left",
    fit: str = "flexible",
) -> LogoResult:
    title = title.strip()
    if not title:
        raise ValueError("Enter a title before generating logo art")

    font_name = resolve_logo_font(style)
    width = _clamp_output_width(width, minimum=24, maximum=240)
    try:
        figlet = Figlet(font=font_name, width=width)
    except Exception as exc:
        raise ValueError(f"Unknown figlet style: {style}") from exc

    plain = _format_generated_block(figlet.renderText(title), justify=justify, fit=fit, width=width)
    height = len(plain.splitlines()) if plain else 0
    return LogoResult(
        plain=plain,
        markup=build_rich_block(plain, color, bold=True),
        font=font_name,
        width=max((len(line) for line in plain.splitlines()), default=0),
        height=height,
    )


def generate_logo_markup(
    title: str,
    style: str,
    color: str,
    *,
    width: int = 120,
    justify: str = "left",
    fit: str = "flexible",
) -> str:
    return generate_logo_result(title, style, color, width=width, justify=justify, fit=fit).markup


def import_art_text(text: str, color: str, *, mode: str = "plain", bold: bool = False, dim: bool = False) -> str:
    content = str(text or "")
    if not content.strip():
        raise ValueError("Nothing to import")

    import_mode = mode.strip().lower() or "plain"
    if import_mode == "markup":
        return content.rstrip()
    if import_mode != "plain":
        raise ValueError("Import mode must be 'plain' or 'markup'")
    return build_rich_block(content, color, bold=bold, dim=dim)


def import_art_file(path: str | Path, color: str, *, mode: str = "plain", bold: bool = False, dim: bool = False) -> str:
    file_path = Path(path).expanduser()
    if not file_path.exists():
        raise FileNotFoundError(f"Art file not found: {file_path}")
    return import_art_text(file_path.read_text(encoding="utf-8"), color, mode=mode, bold=bold, dim=dim)


def _load_image(image_path: str | Path) -> Image.Image:
    path = Path(image_path).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")
    image = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    return image


def _clamp_width(width: int) -> int:
    return max(16, min(60, int(width)))


def _clamp_unit(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _prepare_image(
    image: Image.Image,
    *,
    brightness: float = 1.0,
    contrast: float = 1.0,
    invert: bool = False,
    threshold: int | None = None,
    sharpen: float = 1.0,
    edge_strength: float = 0.0,
) -> Image.Image:
    prepared = image.copy()
    if brightness != 1.0:
        prepared = ImageEnhance.Brightness(prepared).enhance(max(0.1, brightness))
    if contrast != 1.0:
        prepared = ImageEnhance.Contrast(prepared).enhance(max(0.1, contrast))
    if invert:
        prepared = ImageOps.invert(prepared)

    grayscale = prepared.convert("L")
    grayscale = ImageOps.autocontrast(grayscale)

    if sharpen != 1.0:
        grayscale = ImageEnhance.Sharpness(grayscale).enhance(max(0.0, sharpen))

    if edge_strength > 0.0:
        edges = grayscale.filter(ImageFilter.FIND_EDGES)
        grayscale = Image.blend(grayscale, edges, _clamp_unit(edge_strength))

    if threshold is not None:
        normalized_threshold = max(0, min(255, int(threshold)))
        grayscale = grayscale.point(lambda px: 255 if px >= normalized_threshold else 0)

    return grayscale


def _char_height(image: Image.Image, width: int, aspect_factor: float) -> int:
    if image.width <= 0 or image.height <= 0:
        return width
    return max(1, round((image.height / image.width) * width * aspect_factor))


def _render_ramp(image: Image.Image, chars: str, width: int) -> tuple[str, int]:
    height = _char_height(image, width, 0.5)
    resized = image.resize((width, height))
    palette = chars
    steps = len(palette) - 1
    rows: list[str] = []

    for y in range(resized.height):
        chars_row: list[str] = []
        for x in range(resized.width):
            darkness = 1 - (resized.getpixel((x, y)) / 255)
            index = round(darkness * steps)
            chars_row.append(palette[index])
        rows.append("".join(chars_row).rstrip())

    return "\n".join(rows).strip("\n"), height


def _render_braille(image: Image.Image, width: int) -> tuple[str, int]:
    char_height = _char_height(image, width, 0.5)
    resized = image.resize((width * 2, char_height * 4))
    rows: list[str] = []

    for y in range(0, resized.height, 4):
        line = []
        for x in range(0, resized.width, 2):
            bits = 0
            total_darkness = 0.0
            samples = 0

            for dy in range(4):
                for dx in range(2):
                    px = x + dx
                    py = y + dy
                    if px >= resized.width or py >= resized.height:
                        continue
                    darkness = 1 - (resized.getpixel((px, py)) / 255)
                    total_darkness += darkness
                    samples += 1

            average = total_darkness / max(samples, 1)
            threshold = 0.34 if average >= 0.72 else 0.42 if average >= 0.48 else 0.50

            for dy in range(4):
                for dx in range(2):
                    px = x + dx
                    py = y + dy
                    if px >= resized.width or py >= resized.height:
                        continue
                    darkness = 1 - (resized.getpixel((px, py)) / 255)
                    if darkness >= threshold:
                        bits |= BRAILLE_BIT_GRID[dy][dx]

            line.append(chr(0x2800 + bits) if bits else " ")

        rows.append("".join(line).rstrip())

    return "\n".join(rows).strip("\n"), char_height


def generate_hero_markup(
    image_path: str | Path,
    style: str,
    width: int,
    color: str,
    *,
    justify: str = "left",
    fit: str = "flexible",
    brightness: float = 1.0,
    contrast: float = 1.0,
    invert: bool = False,
    threshold: int | None = None,
    sharpen: float = 1.0,
    edge_strength: float = 0.0,
) -> HeroResult:
    style_key = style.strip().lower() or "braille"
    if style_key not in HERO_STYLE_MAP:
        raise ValueError(f"Unknown hero style: {style_key}")

    image = _load_image(image_path)
    image = _prepare_image(
        image,
        brightness=brightness,
        contrast=contrast,
        invert=invert,
        threshold=threshold,
        sharpen=sharpen,
        edge_strength=edge_strength,
    )
    width = _clamp_width(width)

    if HERO_STYLE_MAP[style_key]["renderer"] == "braille":
        plain, height = _render_braille(image, width)
    else:
        plain, height = _render_ramp(image, HERO_STYLE_MAP[style_key]["chars"], width)

    plain = _format_generated_block(plain, justify=justify, fit=fit, width=width)

    return HeroResult(
        markup=build_rich_block(plain, color),
        style=style_key,
        width=width,
        height=height,
    )
